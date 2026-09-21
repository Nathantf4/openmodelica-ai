"""Negative controls against the real runner and its finite/fresh CSV gate."""
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_model", ROOT / "scripts/run_model.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_nonfinite_csv_fails_closed(tmp_path, bad):
    result = tmp_path / "bad.csv"
    result.write_text(f'"time","x"\n0,0\n1,{bad}\n')
    with pytest.raises(ValueError, match="nonfinite"):
        runner.finite_csv(result, 0, 0, 1)


def test_old_result_cannot_satisfy_new_run(tmp_path):
    result = tmp_path / "old.csv"
    result.write_text('"time","x"\n0,0\n1,1\n')
    os.utime(result, (1, 1))
    with pytest.raises(ValueError, match="stale"):
        runner.finite_csv(result, time.time_ns(), 0, 1)


@pytest.mark.parametrize("body", ['"time","x"\n0,0\n0.5,1\n', '"time","x"\n0,0\n0.7,1\n0.6,2\n1,3\n'])
def test_incomplete_or_backward_result_fails(tmp_path, body):
    result = tmp_path / "bad.csv"
    result.write_text(body)
    with pytest.raises(ValueError):
        runner.finite_csv(result, 0, 0, 1)


def invoke(*extra, source=None, model="RLStep"):
    output = ROOT / "artifacts/smoke/runner-tests" / uuid.uuid4().hex
    child = subprocess.run([str(ROOT / "bin/om"), "python3", str(ROOT / "scripts/run_model.py"),
                            str(source or ROOT / "examples/rl_step/model.mo"), model, "--stop", "2",
                            "--output-root", str(output), *extra], cwd=ROOT,
                           text=True, capture_output=True, timeout=180)
    output.mkdir(parents=True, exist_ok=True)
    (output / "child.log").write_text(child.stdout + child.stderr)
    return child


def test_optional_fmu_export_is_fresh_fmi2_archive():
    import zipfile
    child = invoke("--fmu")
    assert child.returncode == 0, child.stdout + child.stderr
    report = json.loads(Path(child.stdout.strip().splitlines()[-1]).read_text())
    fmu = Path(report["fmu"]["path"])
    assert fmu.stat().st_mtime_ns >= report["started_ns"]
    with zipfile.ZipFile(fmu) as archive:
        assert archive.testzip() is None
        assert "modelDescription.xml" in archive.namelist()
        assert any(n.endswith(".so") for n in archive.namelist())
    assert report["fmu"]["fmi_version"] == "2.0"


def override_probe(declaration, value="2", rhs="gain"):
    # The compiler mounts source/code read-only; fixtures belong in artifacts.
    fixture = ROOT / "artifacts/smoke/runner-tests" / uuid.uuid4().hex
    fixture.mkdir(parents=True)
    source = fixture / "model.mo"
    source.write_text(f"model OverrideProbe\n  {declaration}\n"
                      "  Real x(start=0, fixed=true);\nequation\n"
                      f"  der(x)={rhs};\nend OverrideProbe;\n")
    child = invoke("--stop", "1", "--intervals", "10", "--override", f"gain={value}",
                   source=source, model="OverrideProbe")
    report = json.loads(Path(child.stdout.strip().splitlines()[-1]).read_text())
    return child, report


@pytest.mark.parametrize("declaration", [
    "final parameter Real gain=1;",
    "parameter Real gain=1 annotation(Evaluate=true);",
], ids=["final", "evaluated"])
def test_nonchangeable_override_cannot_report_pass(declaration):
    child, report = override_probe(declaration)
    assert child.returncode == 1, json.dumps(report, indent=2)
    assert report["status"] == "FAIL"
    assert "override" in report["error"].lower() and "gain" in report["error"]
    diagnostic = "It is not possible to override the following quantity: gain"
    assert diagnostic in report["simulation"]["messages"]
    assert diagnostic in (Path(report["run_dir"]) / "transcript.jsonl").read_text()
    evidence = report["override_validation"]
    assert evidence["validated"] is False
    assert evidence["parameters"]["gain"]["isValueChangeable"] == "false"
    assert evidence["parameters"]["gain"]["effective_value"] == 1
    with Path(report["result_file"]).open() as stream:
        assert float(list(csv.DictReader(stream))[-1]["x"]) == pytest.approx(1)
    # Independently exercise the metadata gate using this real compiler artifact:
    # even an unchanged requested value and no warning must not bless a final.
    metadata_only = runner.override_evidence(report["run_dir"], {"gain": 1}, report["started_ns"],
                                             1, evidence["readback_line"], "")
    assert metadata_only["validated"] is False
    assert any("not runtime-changeable" in error for error in metadata_only["errors"])


@pytest.mark.parametrize("value", ["2", "0", "1.2345678901234567", "1e-12"])
def test_changeable_real_override_reads_back_and_changes_physics(value):
    child, report = override_probe("parameter Real gain=1;", value)
    assert child.returncode == 0, child.stdout + child.stderr
    assert report["status"] == "PASS"
    assert report["override_validation"]["parameters"]["gain"]["effective_value"] == float(value)
    with Path(report["result_file"]).open() as stream:
        assert float(list(csv.DictReader(stream))[-1]["x"]) == pytest.approx(float(value), rel=1e-8, abs=1e-20)
    if float(value) < 1e-6:
        assert "warning" in report["simulation"]["messages"]
        assert "small value or zero" in report["simulation"]["messages"]


def test_real_overrides_have_compiled_metadata_and_runtime_readback():
    child = invoke("--override", "R=4", "--override", "L=0.25")
    assert child.returncode == 0, child.stdout + child.stderr
    report = json.loads(Path(child.stdout.strip().splitlines()[-1]).read_text())
    evidence = report["override_validation"]
    assert evidence["validated"] is True
    assert Path(evidence["metadata_file"]).is_file()
    for name, value in {"R": 4.0, "L": 0.25}.items():
        item = evidence["parameters"][name]
        assert item["isValueChangeable"] == "true"
        assert item["variability"] == "parameter" and item["type"] == "Real"
        assert item["effective_value"] == value
        assert item["readback_source"] == "simulation.messages (-output)"
    assert evidence["parameters"]["R"]["compiled_start"] == "2.0"
    assert evidence["parameters"]["L"]["compiled_start"] == "0.5"


@pytest.mark.parametrize("declaration,value,rhs", [
    ("parameter Integer gain=1;", "2", "gain"),
    ("parameter Integer gain=1;", "2.5", "gain"),
    ("parameter Boolean gain=false annotation(Evaluate=false);", "0", "if gain then 2 else 1"),
], ids=["integer", "fractional-integer", "boolean"])
def test_nonreal_overrides_are_outside_numeric_real_scope(declaration, value, rhs):
    child, report = override_probe(declaration, value, rhs)
    assert "only scalar Real parameter overrides are supported" in report.get("error", ""), report
    assert child.returncode == 1, child.stdout + child.stderr
    assert report["status"] == "FAIL"


def test_unknown_override_rejected_before_simulation():
    child = invoke("--override", "typoParameter=3")
    assert child.returncode == 1, child.stdout + child.stderr
    report = json.loads(Path(child.stdout.strip().splitlines()[-1]).read_text())
    assert report["status"] == "FAIL"
    assert "unknown parameter" in report["error"].lower()
    assert not any(c["expression"].startswith("simulate(") for c in report["commands"])


@pytest.mark.parametrize("override", ["R=nan", "R=1);system(\"bad\")", "bad-name=2"])
def test_non_numeric_or_injected_override_is_not_modelica_code(override):
    child = invoke("--override", override)
    assert child.returncode == 2
    assert "overrides require" in child.stderr
