"""Real bounded workload controls: host death must remove its exact container."""
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[1]


def container_exists(cid):
    return subprocess.run(['docker','inspect',cid],capture_output=True,timeout=10).returncode == 0


@pytest.mark.parametrize('ending',['timeout','terminate','kill'])
def test_host_cancellation_removes_exact_container(ending):
    out = ROOT/'artifacts/lifecycle-tests'/uuid.uuid4().hex
    out.mkdir(parents=True)
    marker = out/'container.txt'
    code = f'import socket,time; from pathlib import Path; Path({str(marker)!r}).write_text(socket.gethostname()); time.sleep(30)'
    args = [str(ROOT/'bin/om'),'python3','-c',code]
    cid = None
    evidence = {'ending':ending}
    try:
        if ending == 'timeout':
            with pytest.raises(subprocess.TimeoutExpired):
                subprocess.run(args,text=True,capture_output=True,timeout=4)
        else:
            process = subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            deadline = time.monotonic()+8
            while not marker.exists() and time.monotonic()<deadline:
                time.sleep(0.1)
            assert marker.exists(), 'container never became ready'
            if ending == 'terminate':
                process.terminate()
            else:
                process.kill()
            process.communicate(timeout=12)
        assert marker.exists(), 'bounded workload did not record its identity'
        cid = marker.read_text().strip()
        evidence['container_id'] = cid
        assert len(cid)>=12 and all(c in '0123456789abcdef' for c in cid)
        deadline = time.monotonic()+5
        while container_exists(cid) and time.monotonic()<deadline:
            time.sleep(0.1)
        evidence['absent_without_test_cleanup'] = not container_exists(cid)
        assert evidence['absent_without_test_cleanup'], 'timed-out/cancelled workload container survived'
    finally:
        if cid is None and marker.exists():
            cid = marker.read_text().strip()
        if cid and container_exists(cid):
            cleanup = subprocess.run(['docker','rm','-f',cid],capture_output=True,text=True,timeout=15)
            evidence['emergency_test_cleanup'] = cleanup.returncode
        (out/'evidence.json').write_text(json.dumps(evidence,indent=2))


def test_container_deadline_and_stdin_exit_propagation():
    env = dict(os.environ,OPENMODELICA_TIMEOUT_SECONDS='2')
    expired = subprocess.run([str(ROOT/'bin/om'),'python3','-c','import time; time.sleep(30)'],
                             env=env,text=True,capture_output=True,timeout=12)
    assert expired.returncode == 124, expired.stdout+expired.stderr
    echo = subprocess.run([str(ROOT/'bin/om'),'python3','-c','import sys; print(sys.stdin.read()); sys.exit(7)'],
                          input='test-stdin-preserved',text=True,capture_output=True,timeout=20)
    assert echo.returncode == 7, echo.stdout+echo.stderr
    assert echo.stdout.strip() == 'test-stdin-preserved'
