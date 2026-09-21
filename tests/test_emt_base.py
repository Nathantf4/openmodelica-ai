"""Real compiler, independent EMT physics and extracted take-home acceptance."""
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('emt_base', ROOT / 'scripts/emt_base.py')
emt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(emt)


@pytest.fixture(scope='module')
def measured():
    # One full measurement per module; all numeric assertions reuse its CSVs.
    return emt.verify()


@pytest.mark.parametrize('case', ['base', 'fault'])
def test_checked_models(measured, case):
    r = json.loads(Path(measured['runs'][case]['report_path']).read_text())
    assert r['status'] == 'PASS'
    assert 'completed successfully' in r['check']
    assert r['data']['finite'] and r['data']['start'] == 0 and r['data']['stop'] == 3
    assert r['intervals'] >= 30000
    assert r['versions']['Modelica'] == '4.1.0'


def test_steady_state_independent_equivalent_circuit(measured):
    a = measured['checks']['A']
    assert a['pass']
    assert abs(a['simulated_rpm'] / 1440.45 - 1) < .01
    assert abs(a['simulated_current_A'] / 100 - 1) < .03
    assert abs(a['nominal_reference']['torque_Nm'] - 161.4) < 1e-8
    assert abs(a['nominal_reference']['rpm'] - 1440.45) < .01
    assert a['circuit_speed_error_fraction'] < .001
    assert a['circuit_current_error_fraction'] < .003


def test_fault_physics(measured):
    b = measured['checks']['B']
    assert b['pass']
    assert b['voltage_ratio'] <= .01
    assert b['fault_current_error_fraction'] < .03
    assert b['kcl_relative'] < 1e-6
    assert b['minimum_fault_rpm'] < b['prefault_rpm'] - 1
    assert abs(b['recovered_rpm'] / b['prefault_rpm'] - 1) < .01


def test_event_times_read_from_csv(measured):
    c = measured['checks']['C']
    assert c['pass'] and len(c['transition_times_s']) == 2
    assert abs(c['transition_times_s'][0] - 1.5) <= 1e-4
    assert abs(c['transition_times_s'][1] - 1.6) <= 1e-4
    assert c['states_after'] == [1, 0]


def test_runtime_overrides_change_trajectory(measured):
    d = measured['checks']['D']
    assert d['pass']
    assert d['JLoad_readback'] == .58 and d['TLoad_readback'] == 193.68
    assert d['double_inertia_ramp_rpm'] < d['base_ramp_rpm'] - 10
    assert d['double_inertia_t90_s'] > d['base_t90_s'] + .05
    assert d['higher_load_final_rpm'] < d['base_final_rpm'] - 1


def test_missing_class_is_not_exit_code_success(measured):
    e = measured['checks']['E']
    assert e['pass'] and e['raw_omc_exit_code'] == 0
    assert 'not found' in e['diagnostic'] and 'IdealClosingSwitc' in e['diagnostic']
    assert e['csv_count'] == 0
    assert not list(Path(measured['runs']['broken']['run_dir']).glob('*.csv'))


def test_takehome_replay_and_contents(measured):
    assert measured['checks']['F']['pass']
    for replay in measured['replays'].values():
        assert replay['status'] == 'PASS' and len(replay['csvs']) == 2
    with zipfile.ZipFile(measured['zip']) as z:
        assert z.testzip() is None
        assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
        assert not [n for n in z.namelist() if '/Results/' in n and not n.endswith('/')]
        assert set(z.namelist()) == set(measured['zip_members'])
        readme = z.read('emt-base-machine/README.md').decode()
        for phrase in ['electromagnetic transient', '.mos', 'PSCAD', 'single pretty plot']:
            assert phrase in readme
