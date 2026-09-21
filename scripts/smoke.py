#!/usr/bin/env python3
"""Host analytical/plot harness; compiler execution stays in bin/om."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from run_model import ROOT, finite_csv

CASES = {"bouncing": ("bouncing_ball", "BouncingBall", 1.0, 1000),
         "rl": ("rl_step", "RLStep", 2.0, 2000),
         "inertia": ("inertia_step", "InertiaStep", 1.0, 1000),
         "three_phase": ("three_phase", "ThreePhaseLineLoad", .12, 2400)}


def run_model(source, model, stop, intervals, root, overrides=None, expect_success=True):
    argv = [str(ROOT / "bin/om"), "python3", str(ROOT / "scripts/run_model.py"),
            str(source), model, "--stop", str(stop), "--intervals", str(intervals),
            "--output-root", str(root)]
    for name, value in (overrides or {}).items():
        argv.extend(["--override", f"{name}={value}"])
    child = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=180)
    receipt = root / ("child-" + uuid.uuid4().hex + ".log")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(argv) + "\n" + child.stdout + child.stderr)
    if not child.stdout.strip():
        raise AssertionError(f"runner produced no report: {receipt}")
    report_path = Path(child.stdout.strip().splitlines()[-1])
    report = json.loads(report_path.read_text())
    report["report_path"] = str(report_path)
    expected = 0 if expect_success else 1
    if child.returncode != expected or report["status"] != ("PASS" if expect_success else "FAIL"):
        raise AssertionError(f"unexpected runner result: {report_path}: {report.get('error')}; {receipt}")
    return report


def run_mos(example, stop, root, script="run.mos"):
    directory = root / "mos"
    directory.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(example / "model.mo", directory / "model.mo")
    shutil.copyfile(example / script, directory / "run.mos")
    started = time.time_ns()
    child = subprocess.run([str(ROOT / "bin/om"), "omc", "run.mos"], cwd=directory,
                           capture_output=True, text=True, timeout=180)
    (directory / "omc.stdout.log").write_text(child.stdout)
    (directory / "omc.stderr.log").write_text(child.stderr)
    if child.returncode or "completed successfully" not in child.stdout or "Error:" in child.stdout + child.stderr:
        raise AssertionError(f"MOS compile/check failed: {directory}")
    result = directory / "result_res.csv"
    report = finite_csv(result, started, 0, stop)
    report.update({"result_file": str(result), "returncode": child.returncode,
                   "source_sha256": hashlib.sha256((directory / "model.mo").read_bytes()).hexdigest(),
                   "script_sha256": hashlib.sha256((directory / "run.mos").read_bytes()).hexdigest()})
    return report


def data(path):
    rows = np.genfromtxt(path, delimiter=",", names=True, deletechars="", encoding="utf-8")
    return {name.strip('"'): rows[name] for name in rows.dtype.names}


def check_bouncing(d):
    t, h, v = d["time"], d["h"], d["v"]
    impact = np.sqrt(2 / 9.81)
    before = t < impact - 1e-5
    metrics = {"ballistic_height_max_error": float(np.max(np.abs(h[before] - (1 - 0.5 * 9.81 * t[before]**2)))),
               "ballistic_velocity_max_error": float(np.max(np.abs(v[before] + 9.81 * t[before])))}
    jumps = np.flatnonzero((v[:-1] < -1) & (v[1:] > 1))
    assert len(jumps), "no impact and rebound found"
    first = jumps[0]
    metrics["restitution_error"] = float(abs(v[first + 1] / -v[first] - 0.7))
    metrics["first_impact_time_error"] = float(abs(t[first + 1] - impact))
    assert metrics["ballistic_height_max_error"] < 2e-5, metrics
    assert metrics["ballistic_velocity_max_error"] < 2e-5, metrics
    assert metrics["restitution_error"] < 2e-3, metrics
    assert metrics["first_impact_time_error"] < 2e-3, metrics
    return metrics, [("height (m)", h, 1 - 0.5 * 9.81 * np.minimum(t, impact)**2), ("velocity (m/s)", v, None)]


def check_rl(d, R=2, L=0.5, V=10, ts=0.1):
    t = d["time"]
    age = np.maximum(t - ts, 0)
    reference = V / R * (1 - np.exp(-R / L * age))
    derivative = np.where(t > ts, V / L * np.exp(-R / L * age), 0)
    away = np.abs(t - ts) > 1e-7
    metrics = {"current_max_error": float(np.max(np.abs(d["i"] - reference))),
               "derivative_max_error": float(np.max(np.abs(d["di"][away] - derivative[away]))),
               "final_current": float(d["i"][-1])}
    assert metrics["current_max_error"] < 2e-5, metrics
    assert metrics["derivative_max_error"] < 2e-4, metrics
    return metrics, [("current (A)", d["i"], reference), ("der(i) (A/s)", d["di"], derivative)]


def check_inertia(d, J=0.2, tau=2, ts=0.1):
    age = np.maximum(d["time"] - ts, 0)
    speed = tau / J * age
    angle = 0.5 * tau / J * age**2
    metrics = {"speed_max_error": float(np.max(np.abs(d["omega"] - speed))),
               "angle_max_error": float(np.max(np.abs(d["angle"] - angle))),
               "final_speed": float(d["omega"][-1])}
    assert metrics["speed_max_error"] < 2e-5, metrics
    assert metrics["angle_max_error"] < 2e-5, metrics
    return metrics, [("speed (rad/s)", d["omega"], speed), ("angle (rad)", d["angle"], angle)]


def check_three_phase(d):
    t = d["time"]
    w, R, L, peak = 2 * np.pi * 50, 10, .01, 230 * np.sqrt(2)
    impedance = np.sqrt(R**2 + (w * L)**2)
    theta = np.arctan2(w * L, R)
    currents = np.array([d[f"i[{k}]"] for k in (1, 2, 3)])
    waves, reference = [], []
    for k in range(3):
        phase = -2 * np.pi * k / 3
        waves.append(peak * np.sin(w * t + phase))
        reference.append(peak / impedance * (np.sin(w * t + phase - theta)
                         - np.sin(phase - theta) * np.exp(-R / L * t)))
    metrics = {"current_max_error": float(np.max(np.abs(currents - reference))),
               "phase_sum_max": float(np.max(np.abs(currents.sum(axis=0)))),
               "kcl_max": float(max(np.max(np.abs(d[f"kcl[{k}]"])) for k in (1, 2, 3))),
               "source_wave_max_error": float(max(np.max(np.abs(d[f"v[{k}]"] - waves[k-1])) for k in (1, 2, 3))),
               "expected_impedance_ohm": float(impedance), "expected_steady_peak_A": float(peak / impedance)}
    assert metrics["current_max_error"] < 2e-4, metrics
    assert metrics["phase_sum_max"] < 1e-7, metrics
    assert metrics["kcl_max"] < 1e-7, metrics
    assert metrics["source_wave_max_error"] < 1e-7, metrics
    return metrics, [(f"phase {k} current (A)", currents[k-1], reference[k-1]) for k in (1, 2, 3)]


CHECKS = {"bouncing": check_bouncing, "rl": check_rl, "inertia": check_inertia,
          "three_phase": check_three_phase}


def plot(d, signals, target, title):
    fig, axes = plt.subplots(len(signals), 1, figsize=(9, 3 * len(signals)), sharex=True, squeeze=False)
    for ax, (label, signal, reference) in zip(axes[:, 0], signals):
        ax.plot(d["time"], signal, label="OpenModelica", linewidth=1.3)
        if reference is not None:
            ax.plot(d["time"], reference, "--", label="analytical reference", linewidth=1)
        ax.set_ylabel(label)
        ax.grid(alpha=.25)
        ax.legend()
    axes[-1, 0].set_xlabel("time (s)")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(target, dpi=140)
    plt.close(fig)


def standard_case(case, suite):
    folder, model, stop, intervals = CASES[case]
    example = ROOT / "examples" / folder
    assert (example / "model.mo").is_file(), f"missing model for {case}"
    root = suite / case
    root.mkdir()
    mos = run_mos(example, stop, root)
    result = run_model(example / "model.mo", model, stop, intervals, root / "ompython")
    d = data(result["result_file"])
    metrics, signals = CHECKS[case](d)
    mos_metrics, _ = CHECKS[case](data(mos["result_file"]))
    image = root / "signals.png"
    plot(d, signals, image, model)
    return {"run": result, "mos": mos, "metrics": metrics, "mos_metrics": mos_metrics, "plot": str(image)}


def parameter_case(suite):
    results = {}
    for case, overrides, signal in (("rl", {"R": 4, "L": .25, "V": 12}, "i"),
                                    ("inertia", {"J": .4, "tau": 3}, "omega")):
        folder, model, stop, intervals = CASES[case]
        example = ROOT / "examples" / folder
        root = suite / ("parameters-" + case)
        root.mkdir()
        base = run_model(example / "model.mo", model, stop, intervals, root)
        changed = run_model(example / "model.mo", model, stop, intervals, root, overrides)
        assert base["source_sha256"] == changed["source_sha256"]
        assert base["run_dir"] != changed["run_dir"]
        CHECKS[case](data(base["result_file"]))
        d = data(changed["result_file"])
        metrics, signals = CHECKS[case](d, **overrides)
        difference = float(abs(d[signal][-1] - data(base["result_file"])[signal][-1]))
        assert difference > 1, "parameter override did not change physical output"
        mos = run_mos(example, stop, root, "parameters.mos")
        CHECKS[case](data(mos["result_file"]), **overrides)
        baseline = Path(mos["result_file"]).with_name("baseline_res.csv")
        finite_csv(baseline, 0, 0, stop)
        CHECKS[case](data(baseline))
        image = root / "signals.png"
        plot(d, signals, image, model + " parameter override")
        results[case] = {"base": base, "changed": changed, "metrics": metrics,
                         "final_signal_difference": difference, "mos": mos, "plot": str(image)}
    return results


def repair_case(suite):
    root = suite / "repair"
    root.mkdir()
    current = root / "candidate.mo"
    good = (ROOT / "examples/rl_step/model.mo").read_text()
    defective = (ROOT / "examples/seeded_defect/model.mo").read_text()
    current.write_text(good)
    prior = run_model(current, "RLStep", 2, 2000, root)
    prior_bytes = Path(prior["result_file"]).read_bytes()
    current.write_text(defective)
    failed = run_model(current, "RLStep", 2, 2000, root, expect_success=False)
    diagnostics = "\n".join(item.get("diagnostics", "") for item in failed["commands"])
    assert "StepVoltag" in diagnostics and "error" in diagnostics.lower(), diagnostics
    assert not (Path(failed["run_dir"]) / "result_res.csv").exists()
    # A deliberately seeded, deterministic repair, NOT an autonomous model call.
    repaired_text = defective.replace("Sources.StepVoltag source", "Sources.StepVoltage source")
    assert repaired_text != defective
    current.write_text(repaired_text)
    repaired = run_model(current, "RLStep", 2, 2000, root)
    metrics, signals = check_rl(data(repaired["result_file"]))
    assert len({r["run_dir"] for r in (prior, failed, repaired)}) == 3
    assert failed["source_sha256"] != repaired["source_sha256"]
    preserved = Path(prior["result_file"]).read_bytes() == prior_bytes
    assert preserved
    image = root / "repaired.png"
    plot(data(repaired["result_file"]), signals, image, "Seeded typo repaired: RLStep")
    # Also show the raw .mos diagnostic path; do not infer success from exit 0.
    mos_dir = root / "invalid-mos"
    mos_dir.mkdir()
    for filename in ("model.mo", "run.mos"):
        shutil.copyfile(ROOT / "examples/seeded_defect" / filename, mos_dir / filename)
    child = subprocess.run([str(ROOT / "bin/om"), "omc", "run.mos"], cwd=mos_dir,
                           text=True, capture_output=True, timeout=180)
    (mos_dir / "stdout.log").write_text(child.stdout)
    (mos_dir / "stderr.log").write_text(child.stderr)
    assert "StepVoltag" in child.stdout + child.stderr
    assert "Error" in child.stdout + child.stderr
    assert not (mos_dir / "result_res.csv").exists()
    return {"seeded_defect": True, "repair_kind": "scripted class-name correction; no external LLM call",
            "prior": prior, "failed": failed, "repaired": repaired, "diagnostics": diagnostics,
            "prior_result_preserved": preserved, "failed_result_exists": False,
            "invalid_mos_exit": child.returncode, "invalid_mos_dir": str(mos_dir),
            "metrics": metrics, "plot": str(image)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=list(CASES) + ["parameters", "repair"])
    args = parser.parse_args()
    suite = ROOT / "artifacts/smoke" / ("suite-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ-") + uuid.uuid4().hex[:8])
    suite.mkdir(parents=True, exist_ok=False)
    report = {"status": "FAIL", "suite": str(suite), "cases": {}}
    try:
        for case in ([args.only] if args.only else ["bouncing", "rl", "inertia", "parameters", "three_phase", "repair"]):
            if case == "parameters":
                report["cases"][case] = parameter_case(suite)
            elif case == "repair":
                report["cases"][case] = repair_case(suite)
            else:
                report["cases"][case] = standard_case(case, suite)
        report["status"] = "PASS"
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        print(report["error"], file=sys.stderr)
    (suite / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(suite / "summary.json")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
