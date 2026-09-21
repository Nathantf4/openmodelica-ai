"""Actual OMC gates for the public-MSL speed PI demonstration."""
import json
from pathlib import Path
import subprocess
import uuid
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def run_pid(**overrides):
    source=ROOT/'examples/pid_speed/model.mo'
    assert source.is_file(), 'Missing golden speed PI model'
    folder=ROOT/'artifacts/smoke/pid-tests'/uuid.uuid4().hex
    args=[str(ROOT/'bin/om'),'python3',str(ROOT/'scripts/run_model.py'),str(source),'SpeedPIDemo',
          '--stop','3','--intervals','3000','--output-root',str(folder)]
    for k,v in overrides.items():
        args += ['--override',f'{k}={v}']
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=150)
    assert result.returncode==0,result.stdout+result.stderr
    report=json.loads(Path(result.stdout.strip().splitlines()[-1]).read_text())
    assert report['status']=='PASS'
    data=np.genfromtxt(report['result_file'],delimiter=',',names=True,deletechars='')
    return report,data


def test_golden_model_compiles_and_obeys_plant_and_limits():
    report,a=run_pid()
    assert (ROOT/'examples/pid_speed/run.mos').is_file()
    for name in ['time','setpoint','omega','tau','acceleration','xi','uRaw']:
        assert name in a.dtype.names
        assert np.isfinite(a[name]).all()
    assert np.max(np.abs(a['tau']))<=5+1e-8
    assert np.max(a['tau'])>4.999
    assert np.max(np.abs(a['omega'][a['time']<0.5]))<1e-7
    assert np.max(np.abs(0.2*a['acceleration']-(a['tau']-0.1*a['omega'])))<1e-6
    assert report['versions']['Modelica']=='4.1.0'


def test_response_metrics_measure_settling_and_overshoot():
    import importlib.util
    path=ROOT/'scripts/pid_demo.py'
    assert path.is_file(), 'Missing measured-response evaluator'
    spec=importlib.util.spec_from_file_location('pid_demo',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    t=np.array([0,0.5,0.5,1,1.5,2,3.0])
    ref=np.array([0,0,10,10,10,10,10.0])
    w=np.array([0,0,0,12,10.3,10.1,10.0])
    tau=np.array([0,0,5,3,1,1,1.0])
    m=module.response_metrics(t,ref,w,tau)
    assert abs(m['overshoot_percent']-20)<1e-10
    assert m['settling_time_absolute_s']==2
    assert m['iae_rad']==np.trapezoid(np.abs(ref-w),t)
    assert m['torque_limit_ok'] and m['saturation_observed']
    assert not m['target_met']
    w[-1]=9.7
    m=module.response_metrics(t,ref,w,tau)
    assert m['settling_time_absolute_s'] is None
    assert not m['target_met']


def test_retuned_response_meets_targets_and_independent_ode():
    import importlib.util
    path=ROOT/'scripts/pid_demo.py'
    spec=importlib.util.spec_from_file_location('pid_demo',path)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module,'reference_response'), 'Missing independent PI/plant ODE check'
    report,a=run_pid(k=3.0,Ti=0.6)
    m=module.response_metrics(a['time'],a['setpoint'],a['omega'],a['tau'])
    assert m['target_met'] and m['saturation_observed']
    oracle=module.reference_response(a['time'],k=3.0,Ti=0.6)
    assert np.max(np.abs(a['omega']-oracle[:,0]))<1e-3
    assert np.max(np.abs(a['xi']-oracle[:,1]))<1e-3
    assert report['override_validation']['parameters']['k']['effective_value']==3.0
    assert report['override_validation']['parameters']['Ti']['effective_value']==0.6
