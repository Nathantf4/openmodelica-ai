"""Remove one owned container when its wrapper's private pipe closes.

Runs in a separate process/session so SIGKILL of a caller cannot skip cleanup.
Container creation and start are separate; late creates cannot start a workload
once the wrapper is dead. The optional container-side deadline is a second bound.
"""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'org.nathan.openmodelica.run'


def process_identity(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().rpartition(') ')[2].split()[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def inspect_container(name):
    result = subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=8)
    if result.returncode == 0:
        return json.loads(result.stdout)[0]
    if 'no such object' in result.stderr.lower() or 'no such container' in result.stderr.lower():
        return None
    raise RuntimeError(f'Cannot verify container state: {result.stderr.strip()}')


def main():
    fd, token = int(sys.argv[1]), sys.argv[2]
    if not re.fullmatch('[0-9a-f]{32}',token):
        raise ValueError('Invalid owned run identifier')
    name = 'hermes-om-'+token
    journal = ROOT/'artifacts/lifecycle'/f'{token}.json'
    journal.parent.mkdir(parents=True,exist_ok=True)
    state = {'run_id':token,'container_name':name,'events':[], 'absent':False}
    try:
        with os.fdopen(fd) as stream:
            for line in stream:
                event = json.loads(line)
                state['events'].append(event)
                journal.write_text(json.dumps(state,indent=2))
        # The pipe is owned solely by the wrapper. EOF means completion or death.
        for event in state['events']:
            pid = event.get('client_pid')
            identity = event.get('client_start')
            if pid and identity and process_identity(pid) == identity:
                try:
                    os.kill(pid,signal.SIGTERM)
                except ProcessLookupError:
                    pass  # Verified-exited client; container still checked below.
        completed = any(e.get('normal_completion') for e in state['events'])
        deadline = time.monotonic() + (0 if completed else 1.5)
        while True:
            container = inspect_container(name)
            if container is not None:
                if container['Config'].get('Labels',{}).get(LABEL) != token:
                    raise RuntimeError('Refusing to remove a container with mismatched ownership')
                cid = container['Id']
                state['container_id'] = cid
                removed = subprocess.run(['docker','rm','--force',cid],capture_output=True,text=True,timeout=12)
                state['remove_exit'] = removed.returncode
                if inspect_container(cid) is not None:
                    raise RuntimeError(f'Container survived exact-ID cleanup: {removed.stderr}')
                state['absent'] = True
                break
            if time.monotonic() >= deadline:
                state['absent'] = True
                break
            time.sleep(0.1)
        state['status'] = 'CLEAN'
    except Exception as error:
        state['status'] = 'CLEANUP_FAILED'
        state['error'] = f'{type(error).__name__}: {error}'
    finally:
        journal.write_text(json.dumps(state,indent=2))
    return 0 if state['absent'] else 1


if __name__ == '__main__':
    sys.exit(main())
