"""Measured finite-horizon gates for the public MSL speed PI demo."""
from pathlib import Path
import argparse
from datetime import datetime,timezone
import json
import shutil
import subprocess
import sys
import uuid
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def reference_response(times,*,k,Ti,J=0.2,d=0.1,Ni=0.9,step=0.5,target=10.0,limit=5.0,max_step=1e-4):
    """Independent fixed-step RK4 of mechanics + MSL PI tracking anti-windup.

    State is (omega, xi), with u_raw=k*(target-omega+xi),
    J*d(omega)/dt=u-d*omega, d(xi)/dt=(error+(u-u_raw)/(k*Ni))/Ti.
    Integrate only after the known reference step; avoid smearing its jump.
    """
    times=np.asarray(times,dtype=float)
    if not np.isfinite(times).all() or np.any(np.diff(times)<0):
        raise ValueError('Reference requires finite monotone times')
    if min(k,Ti,J,Ni,max_step)<=0 or d<0:
        raise ValueError('Invalid ODE parameters')
    def rhs(y):
        omega,xi=y
        error=target-omega
        raw=k*(error+xi)
        u=min(limit,max(-limit,raw))
        return np.array([(u-d*omega)/J,(error+(u-raw)/(k*Ni))/Ti])
    values=np.zeros((len(times),2))
    y=np.zeros(2)
    clock=step
    for i,t in enumerate(times):
        if t<=step:
            continue
        while t-clock>1e-14:
            h=min(max_step,t-clock)
            a=rhs(y); b=rhs(y+h*a/2); c=rhs(y+h*b/2); e=rhs(y+h*c)
            y=y+h*(a+2*b+2*c+e)/6
            clock+=h
        values[i]=y
    return values


def response_metrics(time,reference,speed,torque,*,target=10.0,step=0.5,limit=5.0):
    t,r,w,u=[np.asarray(x,dtype=float) for x in (time,reference,speed,torque)]
    if len(t)<2 or any(x.shape!=t.shape for x in (r,w,u)):
        raise ValueError('Incomplete response arrays')
    if not all(np.isfinite(x).all() for x in (t,r,w,u)) or np.any(np.diff(t)<0):
        raise ValueError('Nonfinite or backward response')
    if abs(t[0])>1e-8 or abs(t[-1]-3)>1e-8 or target<=0:
        raise ValueError('Expected complete 0..3 second response')
    post=np.flatnonzero(t>=step)
    if not len(post):
        raise ValueError('Missing post-step response')
    outside=post[np.abs(w[post]-target)>0.02*target]
    settling=None
    if not len(outside):
        settling=float(t[post[0]])
    elif outside[-1]<len(t)-1:
        settling=float(t[outside[-1]+1])
    overshoot=float(max(0.0,(np.max(w[post])-target)/target*100))
    saturated=(np.abs(u)>=limit-1e-7).astype(float)
    duration=float(np.trapezoid(saturated,t))
    torque_ok=bool(np.max(np.abs(u))<=limit+1e-8)
    return {
        'overshoot_percent':overshoot,
        'peak_speed_rad_s':float(np.max(w[post])),
        'settling_time_absolute_s':settling,
        'settling_time_after_step_s':None if settling is None else settling-step,
        'settling_definition':'First recorded sample after the last sample outside +/-2%; remains through t=3 s only',
        'iae_rad':float(np.trapezoid(np.abs(r-w),t)),
        'iae_interval_s':[0,3],
        'final_speed_rad_s':float(w[-1]),
        'peak_abs_torque_Nm':float(np.max(np.abs(u))),
        'torque_limit_ok':torque_ok,
        'saturation_observed':duration>1e-3,
        'saturation_duration_sampled_s':duration,
        'target_met':bool(overshoot<10 and settling is not None and settling<=2 and torque_ok),
    }


def invoke(source,model,overrides=None,expect_failure=False):
    dest=ROOT/'artifacts/smoke/pid-demo'/uuid.uuid4().hex
    args=[str(ROOT/'bin/om'),'python3',str(ROOT/'scripts/run_model.py'),str(source),model,
          '--stop','3','--intervals','3000','--output-root',str(dest)]
    for name,value in (overrides or {}).items():
        args += ['--override',f'{name}={value}']
    child=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=150)
    dest.mkdir(parents=True,exist_ok=True)
    (dest/'child.log').write_text(child.stdout+'\nSTDERR\n'+child.stderr)
    if not child.stdout.strip():
        raise RuntimeError(child.stderr)
    report_path=Path(child.stdout.strip().splitlines()[-1])
    report=json.loads(report_path.read_text())
    wanted='FAIL' if expect_failure else 'PASS'
    if report['status']!=wanted or child.returncode!=(1 if expect_failure else 0):
        raise RuntimeError(f'Unexpected compiler result: {report_path}: {report.get("error")}')
    report['report_path']=str(report_path)
    return report


def read_csv(path):
    return np.genfromtxt(path,delimiter=',',names=True,deletechars='')


def comparison_source(golden):
    inner=golden.replace('model SpeedPIDemo ','model Loop ',1).replace('end SpeedPIDemo;','end Loop;')
    icon='Icon(graphics={Rectangle(extent={{-100,60},{100,-60}},lineColor={0,0,127}),Text(extent={{-95,45},{95,-45}},textString="%name",textColor={0,0,127})}),'
    inner=inner.replace('annotation(uses(Modelica',f'annotation({icon}uses(Modelica',1)
    return ('model SpeedPIComparison "Same physical plant, two controller gain sets"\n'+inner+'\n'
        '  Loop baseline(k=0.6,Ti=0.08) annotation(Placement(visible=true,transformation(origin={-70,0},extent={{-45,-30},{45,30}})));\n'
        '  Loop retuned(k=3,Ti=0.6) annotation(Placement(visible=true,transformation(origin={70,0},extent={{-45,-30},{45,30}})));\n'
        '  Modelica.Units.SI.AngularVelocity setpoint,baselineSpeed,retunedSpeed;\n'
        '  Modelica.Units.SI.Torque baselineTorque,retunedTorque;\n'
        'equation\n  setpoint=baseline.setpoint;\n  baselineSpeed=baseline.omega;\n  retunedSpeed=retuned.omega;\n'
        '  baselineTorque=baseline.tau;\n  retunedTorque=retuned.tau;\n'
        '  annotation(uses(Modelica(version="4.1.0")),experiment(StopTime=3,Interval=0.001,Tolerance=1e-8),\n'
        '  Diagram(coordinateSystem(extent={{-140,-80},{140,80}}),graphics={\n'
        '  Text(extent={{-135,75},{135,55}},textString="Same plant; only PI gains change",textColor={0,0,127}),\n'
        '  Text(extent={{-130,-35},{-10,-60}},textString="k=0.6, Ti=0.08 s",textColor={150,60,0}),\n'
        '  Text(extent={{10,-35},{130,-60}},textString="k=3, Ti=0.6 s",textColor={0,110,40})}));\n'
        'end SpeedPIComparison;\n')


def make_pack(output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'artifacts/dad-demo'):
        raise ValueError('Demo output must be under artifacts/dad-demo')
    output.mkdir(parents=True,exist_ok=False)
    pack=output/'openmodelica-speed-pi'
    pack.mkdir()
    source=ROOT/'examples/pid_speed/model.mo'
    golden=source.read_text()
    summary={'created_utc':datetime.now(timezone.utc).isoformat(),'presenting_model':'Astra',
        'selection':'Four measured candidate pairs; selected k=3, Ti=0.6. Not a global optimum.',
        'assumptions':{'J':0.2,'d':0.1,'target_rad_s':10,'step_s':0.5,'torque_limit_Nm':5,'Ni':0.9},
        'scope':'Public MSL toy, no employer data; not engineering certification'}
    arrays={}
    for label,k,Ti,color in [('baseline',0.6,0.08,'#ca6617'),('retuned',3.0,0.6,'#127744')]:
        report=invoke(source,'SpeedPIDemo',{'k':k,'Ti':Ti})
        a=read_csv(report['result_file'])
        arrays[label]=a
        m=response_metrics(a['time'],a['setpoint'],a['omega'],a['tau'])
        oracle=reference_response(a['time'],k=k,Ti=Ti)
        speed_error=float(np.max(np.abs(a['omega']-oracle[:,0])))
        integral_error=float(np.max(np.abs(a['xi']-oracle[:,1])))
        balance=float(np.max(np.abs(0.2*a['acceleration']-a['tau']+0.1*a['omega'])))
        if speed_error>=1e-3 or integral_error>=1e-3 or balance>=1e-6 or not m['torque_limit_ok']:
            raise ValueError('Independent physical checks failed')
        summary[label]={'k':k,'Ti':Ti,'metrics':m,'source_sha256':report['source_sha256'],
            'report':report['report_path'],'csv':report['result_file'],
            'effective_parameters':report['override_validation']['parameters'],
            'independent_speed_max_error':speed_error,'independent_integral_max_error':integral_error,
            'torque_balance_max_error':balance}
        shutil.copy2(report['result_file'],pack/f'{label}.csv')
        fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
        axes[0].plot(a['time'],a['setpoint'],'k--',label='Requested speed')
        axes[0].plot(a['time'],a['omega'],color=color,label=f'{label}: k={k:g}, Ti={Ti:g} s')
        axes[0].fill_between([0.5,3],9.8,10.2,color='#dddddd',alpha=0.6,label='2% band')
        axes[0].set_ylabel('Speed (rad/s)'); axes[0].legend(); axes[0].grid(alpha=0.25)
        axes[1].plot(a['time'],a['tau'],color=color,label='Applied torque')
        axes[1].axhline(5,color='gray',linestyle='--'); axes[1].axhline(-5,color='gray',linestyle='--')
        axes[1].set_ylabel('Torque (N m)'); axes[1].set_xlabel('Time (s)'); axes[1].grid(alpha=0.25)
        axes[1].legend(); fig.suptitle(f'Speed PI — {label} (public MSL toy)')
        fig.tight_layout(); fig.savefig(pack/f'{label}.png',dpi=150); plt.close(fig)
    if not summary['retuned']['metrics']['target_met'] or summary['baseline']['metrics']['target_met']:
        raise ValueError('Before/after demonstration does not satisfy its stated gate')
    if summary['baseline']['source_sha256']!=summary['retuned']['source_sha256']:
        raise ValueError('Plant source changed between tuning runs')
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    axes[0].plot(arrays['baseline']['time'],arrays['baseline']['setpoint'],'k--',label='Requested speed')
    for label,color in [('baseline','#ca6617'),('retuned','#127744')]:
        a=arrays[label]
        axes[0].plot(a['time'],a['omega'],color=color,label=label)
        axes[1].plot(a['time'],a['tau'],color=color,label=label)
    axes[0].fill_between([0.5,3],9.8,10.2,color='#dddddd',alpha=0.6)
    axes[0].axvline(2,color='gray',linestyle=':',label='Settling deadline')
    axes[0].set_ylabel('Speed (rad/s)'); axes[1].set_ylabel('Torque (N m)'); axes[1].set_xlabel('Time (s)')
    for limit in [-5,5]: axes[1].axhline(limit,color='gray',linestyle='--')
    for axis in axes: axis.grid(alpha=0.25); axis.legend()
    fig.suptitle('Same inertia, damping and torque limits — only PI gains changed')
    fig.tight_layout(); fig.savefig(pack/'comparison.png',dpi=150); plt.close(fig)
    comparison=pack/'SpeedPIComparison.mo'
    comparison.write_text(comparison_source(golden))
    comparison_report=invoke(comparison,'SpeedPIComparison')
    c=read_csv(comparison_report['result_file'])
    for label in ['baseline','retuned']:
        m=response_metrics(c['time'],c['setpoint'],c[label+'Speed'],c[label+'Torque'])
        if bool(m['target_met'])!=(label=='retuned'):
            raise ValueError('Visible comparison model disagrees with measured single-loop runs')
    summary['comparison_report']=comparison_report['report_path']
    summary['comparison_model']=str(comparison)
    # Rehearse a deliberately seeded connector error without touching the golden.
    bad=output/'seeded-defect.mo'
    fixed=output/'seeded-repaired.mo'
    renamed=golden.replace('SpeedPIDemo','SpeedPIDemoDefect')
    bad.write_text(renamed.replace('controller.u_m','controller.u_measure'))
    failure=invoke(bad,'SpeedPIDemoDefect',expect_failure=True)
    if 'u_measure' not in failure.get('error',''):
        raise ValueError('Seeded failure did not expose its expected connector diagnostic')
    fixed.write_text(renamed)
    repair=invoke(fixed,'SpeedPIDemoDefect')
    summary['repair']={'seeded':True,'method':'explicitly scripted fixture correction; not spontaneous model failure',
        'failed_status':failure['status'],'repaired_status':repair['status'],
        'failure_report':failure['report_path'],'repair_report':repair['report_path'],'diagnostic':failure['error']}
    shutil.copy2(source,pack/'model.mo')
    (pack/'run.mos').write_text('''// Run from this folder. Opening this script in OMEdit does not execute it.
loadModel(Modelica,{"4.1.0"},requireExactVersion=true);
getErrorString();
loadFile("model.mo");
getErrorString();
checkModel(SpeedPIDemo);
getErrorString();
simulate(SpeedPIDemo,startTime=0,stopTime=3,numberOfIntervals=3000,tolerance=1e-8,outputFormat="csv",fileNamePrefix="baseline",simflags="-override=k=0.6,Ti=0.08 -output=k,Ti");
getErrorString();
simulate(SpeedPIDemo,startTime=0,stopTime=3,numberOfIntervals=3000,tolerance=1e-8,outputFormat="csv",fileNamePrefix="retuned",simflags="-override=k=3,Ti=0.6 -output=k,Ti");
getErrorString();
''')
    (pack/'PROMPTS.md').write_text('''# Frozen Astra prompts

Generate: Using only Modelica Standard Library 4.1.0, model J=0.2 kg.m2 rotational inertia with d=0.1 N.m.s/rad viscous damping. Track a 0 to 10 rad/s speed step at t=0.5 s using LimPID explicitly in PI mode, output limited to +/-5 N.m, initial speed and integrator state zero. Write model.mo and run.mos for a 3-second simulation. Check and simulate with the real compiler, preserve diagnostics and verify fresh finite results. Plot setpoint, speed and torque with units.

Retune: Keep exactly the same plant and limits. Change only k and Ti. Achieve less than 10% overshoot and enter the +/-2% speed band by absolute simulation time 2 s, remaining there through 3 s. Measure both gain pairs and IAE on 0..3 s. Do not silently accept ignored overrides or claim global optimality.

Repair fallback: Deliberately change controller.u_m to the nonexistent controller.u_measure in a separate copy. Say that this is a seeded error, show the actual compiler diagnostic, restore the verified connector and rerun. Do not pretend this was a spontaneous AI mistake.
''')
    portable={k:summary[k] for k in ['presenting_model','selection','assumptions','scope']}
    portable.update({name:{k:summary[name][k] for k in ['k','Ti','metrics','independent_speed_max_error','independent_integral_max_error']} for name in ['baseline','retuned']})
    (pack/'MEASUREMENTS.json').write_text(json.dumps(portable,indent=2))
    (pack/'README.md').write_text('''# Public MSL speed PI example

Generated and rehearsed with Astra, OpenModelica 1.27.1 and Modelica Standard Library 4.1.0. No employer data, extra libraries or private corpus are included. Install OpenModelica and MSL 4.1.0 on the receiving machine.

Open model.mo in OMEdit to inspect the diagram and run the baseline. Open SpeedPIComparison.mo for a self-contained before/after comparison and plot setpoint, baselineSpeed and retunedSpeed; plot baselineTorque and retunedTorque separately.

For the two CSV runs, execute `omc run.mos` from this folder (not by opening the .mos as a model). It writes fresh baseline_res.csv and retuned_res.csv. OMC can return shell exit zero on errors: inspect diagnostics, actual output files and the measured trajectories. The original baseline.csv/retuned.csv and PNGs are retained reference evidence, not newly generated results.

See MEASUREMENTS.json for actual values and their finite-horizon definitions; PROMPTS.md contains the generation/retune/explicitly-seeded-repair prompts. Both runs hit the actuator limit. This demonstrates a controller including tracking anti-windup, not an isolated experimental estimate of anti-windup benefit.

The default model uses the intentionally poor baseline gains; the retuned case changes only k and Ti. Gain selection explored four pairs, not all possible controllers. No noise, delay, motor electrical dynamics or uncertain load was modeled. Compiler success is not engineering certification; this is a public textbook-style toy, not a site model or a replacement for specialist engineering tools.
''')
    archive=output/'openmodelica-speed-pi.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(pack.iterdir()):
            if file.is_file(): z.write(file,Path(pack.name)/file.name)
    summary['zip']=str(archive)
    summary['take_home']=str(pack)
    summary['status']='PASS'
    (output/'summary.json').write_text(json.dumps(summary,indent=2))
    return output/'summary.json'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/dad-demo'/('run-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]))
    args=parser.parse_args()
    print(make_pack(args.output))
