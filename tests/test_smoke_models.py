"""Real compiler integration: each case gets new evidence, never cached success."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def smoke(case):
    script = ROOT / "scripts/smoke.py"
    assert script.is_file(), "compiler-driven smoke harness is not implemented"
    child = subprocess.run([sys.executable, str(script), "--only", case], cwd=ROOT,
                           text=True, capture_output=True, timeout=240)
    assert child.returncode == 0, child.stdout + child.stderr
    report = json.loads(Path(child.stdout.strip().splitlines()[-1]).read_text())
    assert report["status"] == "PASS", report
    return report


def test_rl_step_matches_analytic_current_and_derivative():
    report = smoke("rl")
    case = report["cases"]["rl"]
    assert case["metrics"]["current_max_error"] < 2e-5
    assert case["metrics"]["derivative_max_error"] < 2e-4
    assert Path(case["plot"]).is_file()
    assert case["mos"]["finite"] is True


def test_inertia_torque_step_matches_analytic_speed():
    case = smoke("inertia")["cases"]["inertia"]
    assert case["metrics"]["speed_max_error"] < 2e-5
    assert case["metrics"]["angle_max_error"] < 2e-5
    assert Path(case["plot"]).is_file()


def test_parameter_reruns_change_physics_without_changing_source():
    case = smoke("parameters")["cases"]["parameters"]
    for name in ("rl", "inertia"):
        pair = case[name]
        assert pair["base"]["source_sha256"] == pair["changed"]["source_sha256"]
        assert pair["base"]["run_dir"] != pair["changed"]["run_dir"]
        assert pair["final_signal_difference"] > 1
        assert pair["changed"]["overrides"]
        assert Path(pair["plot"]).is_file()


def test_three_phase_source_line_load_balance_and_impedance():
    case = smoke("three_phase")["cases"]["three_phase"]
    assert case["metrics"]["current_max_error"] < 2e-4
    assert case["metrics"]["phase_sum_max"] < 1e-7
    assert case["metrics"]["kcl_max"] < 1e-7
    assert case["metrics"]["source_wave_max_error"] < 1e-7
    assert Path(case["plot"]).is_file()


def test_seeded_defect_reports_diagnostics_then_repairs_without_stale_success():
    case = smoke("repair")["cases"]["repair"]
    assert case["seeded_defect"] is True
    assert "StepVoltag" in case["diagnostics"]
    assert "error" in case["diagnostics"].lower()
    assert case["failed"]["status"] == "FAIL"
    assert case["repaired"]["status"] == "PASS"
    assert case["failed"]["source_sha256"] != case["repaired"]["source_sha256"]
    assert case["prior_result_preserved"] is True
    assert case["failed_result_exists"] is False
    assert len({case[k]["run_dir"] for k in ("prior", "failed", "repaired")}) == 3


def test_bouncing_ball_real_mos_and_ompython():
    report = smoke("bouncing")
    case = report["cases"]["bouncing"]
    assert case["metrics"]["ballistic_height_max_error"] < 2e-5
    assert case["metrics"]["restitution_error"] < 2e-3
    assert Path(case["plot"]).is_file()
    assert case["mos"]["finite"] is True
    assert case["run"]["status"] == "PASS"
    assert case["run"]["versions"]["Modelica"] == "4.1.0"
