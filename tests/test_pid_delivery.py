"""The takeaway must run from its extracted layout, not just exist."""
import csv
import json
from pathlib import Path
import subprocess
import time
import uuid
import zipfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def test_demo_pack_is_measured_and_native_portable():
    out=ROOT/'artifacts/dad-demo'/('acceptance-'+uuid.uuid4().hex)
    result=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/pid_demo.py'),
                           '--output',str(out)],cwd=ROOT,capture_output=True,text=True,timeout=220)
    assert result.returncode==0,result.stdout+result.stderr
    assert (out/'summary.json').is_file(),'Demo CLI did not produce a measured pack'
    summary=json.loads((out/'summary.json').read_text())
    assert summary['retuned']['metrics']['target_met']
    assert not summary['baseline']['metrics']['target_met']
    assert summary['baseline']['source_sha256']==summary['retuned']['source_sha256']
    assert summary['retuned']['metrics']['iae_rad']<summary['baseline']['metrics']['iae_rad']
    assert summary['repair']['seeded'] and summary['repair']['failed_status']=='FAIL'
    assert summary['repair']['repaired_status']=='PASS'
    for case in ['baseline','retuned']:
        assert summary[case]['independent_speed_max_error']<1e-3
    extract=out/'portable-native-replay'
    with zipfile.ZipFile(summary['zip']) as archive:
        assert archive.testzip() is None
        assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in archive.namelist())
        archive.extractall(extract)
    pack=extract/'openmodelica-speed-pi'
    for name in ['model.mo','run.mos','baseline.csv','retuned.csv','baseline.png','retuned.png','comparison.png','PROMPTS.md','README.md']:
        assert (pack/name).is_file(),name
    assert '/home/nathan' not in (pack/'run.mos').read_text()
    assert '/home/nathan' not in (pack/'model.mo').read_text()
    started=time.time_ns()
    native=subprocess.run([str(Path.home()/'.local/bin/omc-native'),'run.mos'],cwd=pack,
                          capture_output=True,text=True,timeout=100)
    (out/'portable-native.log').write_text(native.stdout+native.stderr)
    assert native.returncode==0,native.stdout+native.stderr
    for case in ['baseline','retuned']:
        fresh=pack/f'{case}_res.csv'
        assert fresh.is_file() and fresh.stat().st_mtime_ns>=started,native.stdout
        a=np.genfromtxt(fresh,delimiter=',',names=True,deletechars='')
        expected=np.genfromtxt(pack/f'{case}.csv',delimiter=',',names=True,deletechars='')
        assert np.isfinite(a['omega']).all()
        assert a['time'][-1]==3
        # Event grids can differ; compare on a shared regular grid away from the step.
        grid=np.linspace(0.501,3,1000)
        error=np.max(np.abs(np.interp(grid,a['time'],a['omega'])-np.interp(grid,expected['time'],expected['omega'])))
        assert error<1e-3
