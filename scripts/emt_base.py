#!/usr/bin/env python3
"""Independent EMT checks and take-home replay; uses the existing checked runner."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time
import uuid
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'examples/emt_base_machine'
EVIDENCE = ROOT / 'artifacts/emt-base'
STOP = 3.0
DT = 1e-4
R_LINE = .005
L_LINE = .03 / (2 * math.pi * 50)
R_FAULT = 1e-5


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def note(message):
    with (EVIDENCE / 'LOG.md').open('a') as f:
        f.write(f'- {datetime.now(timezone.utc).isoformat()} {message}\n')
    print(message, flush=True)


def equivalent_circuit(*, Rline=0., Lline=0., quadratic=False, TLoad=161.4):
    """Plain complex arithmetic, independent of Modelica equations/powerBalance.

    Xs=Xr=3, sigma=.0667; split leakage and mutual reactance exactly as the
    documented default data. Solve the stable, low-slip motoring root.
    """
    if Rline < 0 or Lline < 0 or TLoad <= 0:
        raise ValueError('Require nonnegative line impedance and positive load')
    omega_s = 2 * math.pi * 50  # electrical rad/s; p=2 pole pairs
    xm = 3 * math.sqrt(1 - .0667)
    xs_sigma = 3 - xm

    def point(slip):
        zr = .04 / slip + 1j * xs_sigma
        zm = 1j * xm
        parallel = zm * zr / (zm + zr)
        impedance = Rline + 1j * omega_s * Lline + .03 + 1j * xs_sigma + parallel
        stator = 100 / impedance
        rotor = stator * parallel / zr
        torque = 3 * 2 * abs(rotor)**2 * (.04 / slip) / omega_s
        rpm = 1500 * (1 - slip)
        load = TLoad * (rpm / 1440.45)**2 if quadratic else TLoad
        return torque, rpm, abs(stator), abs(100 - stator * (Rline + 1j * omega_s * Lline)), load

    # This bracket covers the default and the explicitly tested load override.
    # ponytail: low-slip root only; add torque-curve branch selection for general sizing.
    lo, hi = 1e-8, .1
    if point(lo)[0] >= point(lo)[4] or point(hi)[0] <= point(hi)[4]:
        raise ValueError('No stable operating root in the tested slip bracket')
    for _ in range(80):
        s = (lo + hi) / 2
        torque, _, _, _, load = point(s)
        if torque < load:
            lo = s
        else:
            hi = s
    torque, rpm, current, voltage, load = point((lo + hi) / 2)
    return {'slip': (lo + hi) / 2, 'rpm': rpm, 'current_A': current,
            'torque_Nm': torque, 'load_Nm': load, 'terminal_voltage_V': voltage,
            'Xs_sigma_ohm': xs_sigma, 'Xr_sigma_ohm': xs_sigma, 'Xm_ohm': xm,
            'Rline_ohm': Rline, 'Lline_H': Lline, 'quadratic': quadratic}


def read_csv(path):
    with Path(path).open(newline='') as f:
        names = next(csv.reader(f))
    if len(set(names)) != len(names):
        raise ValueError(f'Duplicate CSV columns: {path}')
    a = np.loadtxt(path, delimiter=',', skiprows=1, dtype=[(n, float) for n in names])
    if len(a) < 2 or not all(np.isfinite(a[n]).all() for n in a.dtype.names):
        raise ValueError(f'Incomplete/nonfinite CSV: {path}')
    if a['time'][0] != 0 or a['time'][-1] != STOP or np.any(np.diff(a['time']) < 0):
        raise ValueError(f'Wrong time horizon/order: {path}')
    return a


def window(a, name, start, stop, rms=False):
    """Time-weighted measurement, clipping exactly to cycle boundaries.

    Keep the post-event row at duplicate times; our measurement windows avoid
    switch instants. Uniform resampling prevents adaptive event rows biasing RMS.
    """
    t, x = a['time'], a[name]
    keep = np.r_[np.diff(t) > 0, True]
    grid = np.linspace(start, stop, round((stop - start) / DT) + 1)
    y = np.interp(grid, t[keep], x[keep])
    v = float(np.trapezoid(y*y if rms else y, grid) / (stop - start))
    return math.sqrt(v) if rms else v


def physics(base, fault, inertia, load, reports):
    nominal = equivalent_circuit()
    constant_line = equivalent_circuit(Rline=R_LINE, Lline=L_LINE)
    operating = equivalent_circuit(Rline=R_LINE, Lline=L_LINE, quadratic=True)
    rpm = float(base['aimc.wMechanical'][-1] * 30 / math.pi)
    current = window(base, 'aimc.is[1]', 2.96, 3, rms=True)
    a = {'nominal_reference': nominal, 'constant_load_with_line': constant_line,
         'quadratic_operating_reference': operating,
         'simulated_rpm': rpm, 'simulated_current_A': current,
         'simulated_load_Nm': window(base, 'loadTorque.tau', 2.96, 3) * -1,
         'simulated_terminal_voltage_V': window(base, 'terminalVRMS', 2.96, 3),
         'speed_error_fraction': abs(rpm / 1440.45 - 1),
         'current_error_fraction': abs(current / 100 - 1),
         'circuit_speed_error_fraction': abs(rpm / operating['rpm'] - 1),
         'circuit_current_error_fraction': abs(current / operating['current_A'] - 1),
         'steady_speed_span_rpm': float(np.ptp(base['aimc.wMechanical'][base['time'] >= 2.9]) * 30 / math.pi)}
    a['pass'] = (a['speed_error_fraction'] < .01 and a['current_error_fraction'] < .03
                 and a['circuit_speed_error_fraction'] < .001 and a['circuit_current_error_fraction'] < .003
                 and a['steady_speed_span_rpm'] < .1)
    t = fault['time']
    source = np.column_stack([fault[f'iSource[{j}]'] for j in (1, 2, 3)])
    pre_v = window(fault, 'terminalVRMS', 1.44, 1.48)
    in_fault = (t > 1.5 + 1e-8) & (t < 1.6 - 1e-8)
    predicted_current = 100 / abs(R_LINE + R_FAULT + 1j * 2 * math.pi * 50 * L_LINE)
    # Exact two cycles ends immediately before clearing (avoid the event row).
    measured_currents = [window(fault, f'iSource[{j}]', 1.56 - DT, 1.6 - DT, rms=True) for j in (1, 2, 3)]
    kcl = float(np.max(np.abs(np.sum(source, axis=1))))
    pre_speed = window(fault, 'aimc.wMechanical', 1.44, 1.48) * 30 / math.pi
    b = {'prefault_voltage_V': pre_v,
         'maximum_fault_voltage_V': float(np.max(fault['terminalVRMS'][in_fault])),
         'voltage_ratio': float(np.max(fault['terminalVRMS'][in_fault])) / pre_v,
         'predicted_fault_current_A': predicted_current, 'measured_fault_currents_A': measured_currents,
         'fault_current_error_fraction': max(abs(i / predicted_current - 1) for i in measured_currents),
         'measurement_window_s': [1.56 - DT, 1.6 - DT],
         'line_time_constant_s': L_LINE / (R_LINE + R_FAULT),
         'kcl_absolute_A': kcl, 'kcl_relative': kcl / float(np.max(np.abs(source))),
         'prefault_rpm': pre_speed,
         'minimum_fault_rpm': float(np.min(fault['aimc.wMechanical'][in_fault]) * 30 / math.pi),
         'recovered_rpm': float(fault['aimc.wMechanical'][-1] * 30 / math.pi)}
    peak = int(np.argmax(fault['terminalVRMS']))
    b['maximum_clearing_voltage_V'] = float(fault['terminalVRMS'][peak])
    b['clearing_peak_time_s'] = float(t[peak])
    b['clearing_voltage_limitation'] = ('Ideal interruption of inductive current with no arc or capacitance; '
                                        'the off-conductance sets this nonphysical peak. Not an insulation/surge prediction.')
    b['pass'] = (b['voltage_ratio'] <= .01 and b['fault_current_error_fraction'] < .03
                 and b['kcl_relative'] < 1e-6 and b['minimum_fault_rpm'] < pre_speed - 1
                 and abs(b['recovered_rpm'] / pre_speed - 1) < .01)
    state = fault['faultSwitch.control[1]'].astype(int)
    changes = np.flatnonzero(np.diff(state)) + 1
    c = {'transition_times_s': t[changes].tolist(), 'states_after': state[changes].tolist()}
    c['pass'] = (len(changes) == 2 and state[0] == 0 and c['states_after'] == [1, 0]
                 and all(abs(x - y) <= DT for x, y in zip(c['transition_times_s'], [1.5, 1.6])))
    for j in (2, 3):
        c['pass'] = bool(c['pass'] and np.array_equal(state, fault[f'faultSwitch.control[{j}]']))

    def ramp(data):
        speed = data['aimc.wMechanical'] * 30 / math.pi
        indices = np.flatnonzero(speed >= .9 * rpm)
        return float(np.interp(.5, data['time'], speed)), float(data['time'][indices[0]]) if len(indices) else None

    ramp_base, t90_base = ramp(base)
    ramp_inertia, t90_inertia = ramp(inertia)
    d = {'JLoad_readback': reports['inertia']['override_validation']['parameters']['JLoad']['effective_value'],
         'TLoad_readback': reports['load']['override_validation']['parameters']['TLoad']['effective_value'],
         'ramp_measurement_time_s': .5, 'base_ramp_rpm': ramp_base,
         'double_inertia_ramp_rpm': ramp_inertia, 'base_t90_s': t90_base,
         'double_inertia_t90_s': t90_inertia, 'base_final_rpm': rpm,
         'double_inertia_final_rpm': float(inertia['aimc.wMechanical'][-1] * 30 / math.pi),
         'higher_load_final_rpm': float(load['aimc.wMechanical'][-1] * 30 / math.pi)}
    d['pass'] = (d['JLoad_readback'] == .58 and d['TLoad_readback'] == 193.68
                 and ramp_inertia < ramp_base - 10 and t90_base is not None and t90_inertia is not None
                 and t90_inertia > t90_base + .05 and d['higher_load_final_rpm'] < rpm - 1)
    return {'A': a, 'B': b, 'C': c, 'D': d}


def invoke(folder, label, source, model, overrides=None, broken=False):
    # The unmodified runner resolves its workspace from __file__. An immutable
    # byte-identical evidence copy keeps all generated files within this lane.
    workspace = folder / label / 'workspace'
    (workspace / 'scripts').mkdir(parents=True)
    runner = workspace / 'scripts/run_model.py'
    snapshot = workspace / source.name
    shutil.copy2(ROOT / 'scripts/run_model.py', runner)
    shutil.copy2(source, snapshot)
    assert sha256(runner) == sha256(ROOT / 'scripts/run_model.py')
    assert sha256(snapshot) == sha256(source)
    output = workspace / 'artifacts/smoke'
    cmd = [str(ROOT / 'bin/om'), 'python3', str(runner),
           str(snapshot), model, '--stop', str(STOP), '--intervals', str(round(STOP / DT)),
           '--output-root', str(output)]
    for key, value in (overrides or {}).items():
        cmd += ['--override', f'{key}={value}']
    begin = time.perf_counter()
    child = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=240)
    (folder / f'{label}-runner.log').write_text(child.stdout + '\nSTDERR\n' + child.stderr)
    path = Path(child.stdout.strip().splitlines()[-1]) if child.stdout.strip() else None
    if path is None or not path.is_file():
        raise RuntimeError(f'No runner report: {folder}/{label}-runner.log')
    report = json.loads(path.read_text())
    report.update(report_path=str(path), command=cmd, wall_seconds=time.perf_counter() - begin,
                  original_source=str(source), original_source_sha256=sha256(source))
    save(folder / f'{label}-report.json', report)
    note(f'{label}: {report["status"]}; report {path}; {report["wall_seconds"]:.3f} s')
    if report['status'] != ('FAIL' if broken else 'PASS') or child.returncode != (1 if broken else 0):
        raise RuntimeError(f'Unexpected checked run: {path}: {report.get("error")}')
    return report


def negative_control(folder, report):
    dest = folder / 'raw-negative'
    dest.mkdir()
    source = PACK / 'Fixtures/BrokenMissingClass.mo'
    shutil.copy2(source, dest / source.name)
    script = '''loadModel(Modelica,{"4.1.0"},requireExactVersion=true);
loadFile("BrokenMissingClass.mo");
checkModel(BrokenMissingClass);
getErrorString();
simulate(BrokenMissingClass,stopTime=3,outputFormat="csv");
getErrorString();
'''
    (dest / 'broken.mos').write_text(script)
    p = subprocess.run(['omc-native', 'broken.mos'], cwd=dest, text=True, capture_output=True, timeout=30)
    diagnostic = p.stdout + p.stderr
    (dest / 'raw-omc.log').write_text(diagnostic)
    csv_count = len(list(dest.glob('*.csv'))) + len(list(Path(report['run_dir']).glob('*.csv')))
    return {'pass': p.returncode == 0 and 'not found' in diagnostic and 'IdealClosingSwitc' in diagnostic
                    and 'not found' in report.get('error', '') and csv_count == 0,
            'raw_omc_exit_code': p.returncode, 'csv_count': csv_count,
            'diagnostic': diagnostic, 'log': str(dest / 'raw-omc.log')}


def plots(folder, arrays):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    paths = []
    for label in ('base', 'fault'):
        a = arrays[label]
        fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
        for j in (1, 2, 3):
            axes[0].plot(a['time'], a[f'aimc.is[{j}]'], lw=.6, label=f'stator {j}')
        axes[0].set_ylabel('Current (A)'); axes[0].legend(loc='upper right', ncol=3)
        axes[1].plot(a['time'], a['terminalVRMS']); axes[1].set_ylabel('Terminal magnitude (V)')
        if label == 'fault':
            axes[1].set_yscale('symlog', linthresh=1)
            axes[1].set_title('Includes ideal clearing spike; symlog scale, no surge prediction', fontsize=10)
        axes[2].plot(a['time'], a['aimc.wMechanical'] * 30 / math.pi); axes[2].set_ylabel('Speed (rpm)')
        axes[3].plot(a['time'], a['aimc.tauElectrical']); axes[3].set_ylabel('Torque (N m)')
        axes[3].set_xlabel('Time (s)'); fig.suptitle(f'{label}: instantaneous machine transient')
        fig.tight_layout(); path = folder / f'{label}.png'; fig.savefig(path, dpi=140); plt.close(fig)
        paths.append(str(path))
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    a = arrays['fault']; mask = (a['time'] >= 1.47) & (a['time'] <= 1.65)
    for j in (1, 2, 3):
        axes[0].plot(a['time'][mask], a[f'iSource[{j}]'][mask], label=f'source {j}')
        axes[1].plot(a['time'][mask], a[f'faultSwitch.i[{j}]'][mask], label=f'fault {j}')
    for ax in axes:
        ax.set_ylabel('Current (A)'); ax.legend(ncol=3); ax.grid(alpha=.2)
    axes[1].set_xlabel('Time (s)'); fig.tight_layout()
    path = folder / 'fault-currents.png'; fig.savefig(path, dpi=140); plt.close(fig); paths.append(str(path))
    fig, ax = plt.subplots(figsize=(9, 4))
    for label in ('base', 'inertia', 'load'):
        a = arrays[label]
        ax.plot(a['time'], a['aimc.wMechanical'] * 30 / math.pi, label=label)
    ax.set(xlabel='Time (s)', ylabel='Speed (rpm)'); ax.legend(); fig.tight_layout()
    path = folder / 'overrides.png'; fig.savefig(path, dpi=140); plt.close(fig); paths.append(str(path))
    return paths


def replay(pack, log, python=False):
    if list((pack / 'Results').glob('*.csv')):
        raise ValueError('Replay requires a fresh Results directory')
    cmd = ([str(ROOT / 'bin/om'), 'python3', 'Scripts/check_and_simulate.py'] if python
           else ['omc-native', 'Scripts/check_and_simulate.mos'])
    started = time.time_ns(); begin = time.perf_counter()
    p = subprocess.run(cmd, cwd=pack, text=True, capture_output=True, timeout=240)
    text = p.stdout + '\nSTDERR\n' + p.stderr
    log.write_text(text)
    if any(line.startswith('FAIL:') for line in text.splitlines()):
        raise RuntimeError(f'Replay gate failed: {log}')
    for marker in ['PASS: EmtMachineBase', 'PASS: EmtMachineBaseFault', 'EXPECTED_FAIL: BrokenMissingClass']:
        if marker not in text:
            raise RuntimeError(f'Missing {marker}: {log}')
    if p.returncode != 0 or 'not found' not in text:
        raise RuntimeError(f'Wrong replay diagnostics: {log}')
    csvs = []
    for model in ('EmtMachineBase', 'EmtMachineBaseFault'):
        path = pack / 'Results' / f'{model}_res.csv'
        if not path.is_file() or path.stat().st_mtime_ns < started:
            raise RuntimeError(f'Missing/stale replay CSV: {path}')
        a = read_csv(path)
        csvs.append({'path': str(path), 'sha256': sha256(path), 'rows': len(a), 'last_time': float(a['time'][-1])})
    if len(list(pack.rglob('*.csv'))) != 2:
        raise RuntimeError(f'Unexpected CSV/negative-control result: {pack}')
    result = {'status': 'PASS', 'command': cmd, 'directory': str(pack), 'log': str(log),
              'exit_code': p.returncode, 'wall_seconds': time.perf_counter() - begin, 'csvs': csvs}
    save(log.with_suffix('.json'), result)
    note(f'Replay PASS: {log}; {result["wall_seconds"]:.3f} s')
    return result


def build_zip(folder):
    archive = ROOT / 'deliverables/emt-base-machine.zip'
    archive.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(PACK.rglob('*')):
            relative = path.relative_to(PACK)
            if 'Results' not in relative.parts and path.is_file():
                z.write(path, Path('emt-base-machine') / relative)
        z.writestr('emt-base-machine/Results/', '')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failure')
        members = z.namelist()
        manifest = {name: hashlib.sha256(z.read(name)).hexdigest() for name in members if not name.endswith('/')}
    save(folder / 'zip-manifest.json', {'zip': str(archive), 'sha256': sha256(archive), 'members': manifest})
    return archive, members


def verify():
    folder = EVIDENCE / 'runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    summary = {'status': 'FAIL', 'directory': str(folder), 'created_utc': datetime.now(timezone.utc).isoformat(),
               'runs': {}, 'checks': {}, 'replays': {}, 'source_hashes': {
                   str(p.relative_to(ROOT)): sha256(p) for p in sorted(PACK.rglob('*')) if p.is_file()},
               'harness_sha256': sha256(__file__)}
    save(folder / 'summary.json', summary)
    try:
        for label, model, overrides in [('base', 'EmtMachineBase', {}), ('fault', 'EmtMachineBaseFault', {}),
                                        ('inertia', 'EmtMachineBase', {'JLoad': .58}),
                                        ('load', 'EmtMachineBase', {'TLoad': 193.68})]:
            summary['runs'][label] = invoke(folder, label, PACK / 'Models' / f'{model}.mo', model, overrides)
            save(folder / 'summary.json', summary)
        summary['runs']['broken'] = invoke(folder, 'broken', PACK / 'Fixtures/BrokenMissingClass.mo',
                                           'BrokenMissingClass', broken=True)
        arrays = {k: read_csv(v['result_file']) for k, v in summary['runs'].items() if k != 'broken'}
        summary['checks'] = physics(*(arrays[k] for k in ('base', 'fault', 'inertia', 'load')), summary['runs'])
        summary['checks']['E'] = negative_control(folder, summary['runs']['broken'])
        summary['plots'] = plots(folder, arrays)
        save(folder / 'summary.json', summary)
        if not all(c['pass'] for c in summary['checks'].values()):
            raise ValueError('Failed physics/negative gate: ' + ', '.join(k for k, v in summary['checks'].items() if not v['pass']))
        takehome = EVIDENCE / 'takehome' / folder.name
        copied = takehome / 'copy/emt-base-machine'
        shutil.copytree(PACK, copied)
        summary['replays']['copy'] = replay(copied, folder / 'copy-replay.log')
        archive, members = build_zip(folder)
        summary.update(zip=str(archive), zip_members=members, zip_sha256=sha256(archive))
        with zipfile.ZipFile(archive) as z:
            z.extractall(takehome / 'extracted')
        summary['replays']['zip'] = replay(takehome / 'extracted/emt-base-machine', folder / 'zip-replay.log')
        python_pack = takehome / 'python/emt-base-machine'
        shutil.copytree(PACK, python_pack)
        summary['replays']['python'] = replay(python_pack, folder / 'python-replay.log', python=True)
        summary['checks']['F'] = {'pass': all(r['status'] == 'PASS' for r in summary['replays'].values())}
        summary['csv_count'] = 4 + sum(len(r['csvs']) for r in summary['replays'].values())
        current_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in sorted(PACK.rglob('*')) if p.is_file()}
        if current_hashes != summary['source_hashes']:
            raise ValueError('Package sources changed during verification; rerun after edits')
        summary['status'] = 'PASS'
        note(f'All A-F PASS: {folder}/summary.json; {summary["csv_count"]} fresh CSVs')
    except Exception as error:
        summary['error'] = f'{type(error).__name__}: {error}'
        note(f'Verification FAILED: {folder}/summary.json; {summary["error"]}')
        raise
    finally:
        save(folder / 'summary.json', summary)
        (EVIDENCE / 'latest-run.txt').write_text(str(folder / 'summary.json') + '\n')
    return summary


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = verify()
    print(Path(result['directory']) / 'summary.json')
