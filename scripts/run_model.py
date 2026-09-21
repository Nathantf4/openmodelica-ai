#!/usr/bin/env python3
"""Compile and simulate one trusted local .mo in a new evidence directory.

Run inside the pinned toolchain: bin/om python3 scripts/run_model.py MODEL CLASS.
Modelica is executable code; input validation is not a security sandbox.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import sys
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*\Z")


def finite_csv(path, started_ns, start, stop):
    """Validate every numeric cell, monotone time, freshness and full horizon."""
    path = Path(path)
    if not path.is_file() or path.stat().st_mtime_ns < started_ns:
        raise ValueError("missing or stale simulation result")
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "time" not in reader.fieldnames:
            raise ValueError("result lacks time column")
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("duplicate CSV columns")
        rows = []
        for row in reader:
            converted = {k: float(v) for k, v in row.items()}
            if not all(math.isfinite(v) for v in converted.values()):
                raise ValueError("nonfinite simulation result")
            rows.append(converted)
    if len(rows) < 2:
        raise ValueError("insufficient result rows")
    times = [row["time"] for row in rows]
    if any(b < a for a, b in zip(times, times[1:])):
        raise ValueError("nonmonotone simulation time")
    if abs(times[0] - start) > 1e-8 or abs(times[-1] - stop) > 1e-8:
        raise ValueError("incomplete simulation time horizon")
    return {"rows": len(rows), "columns": reader.fieldnames,
            "finite": True, "start": times[0], "stop": times[-1]}


def override_evidence(run, overrides, started_ns, stop, messages, diagnostics):
    """Check compiled applicability and read actual runtime values, not requests.

    result_init.xml holds compiled defaults, NOT effective override values.
    The pinned runtime's -output flag prints parameter values with %.20g.
    """
    metadata = Path(run) / "result_init.xml"
    evidence = {"validated": False, "metadata_file": str(metadata), "parameters": {}, "errors": []}
    errors = evidence["errors"]
    for line in (messages + "\n" + diagnostics).splitlines():
        if any(text in line.lower() for text in (
                "it is not possible to override", "override variable name not found",
                "failed to parse override")):
            errors.append(line)
    try:
        if not metadata.is_file() or metadata.stat().st_mtime_ns < started_ns:
            raise ValueError("missing or stale compiled override metadata")
        variables = ET.parse(metadata).findall(".//ScalarVariable")
        evidence["metadata_sha256"] = hashlib.sha256(metadata.read_bytes()).hexdigest()
        for name in overrides:
            matches = [v for v in variables if v.get("name") == name]
            if len(matches) != 1:
                errors.append(f"override {name}: missing or ambiguous compiled parameter metadata")
                continue
            variable = matches[0]
            item = {key: variable.get(key) for key in ("variability", "isValueChangeable", "causality", "alias")}
            value_type = next(iter(variable), None)
            item["type"] = value_type.tag if value_type is not None else None
            item["compiled_start"] = value_type.get("start") if value_type is not None else None
            evidence["parameters"][name] = item
            if item["type"] != "Real":
                errors.append(f"override {name}: only scalar Real parameter overrides are supported "
                              f"(compiled type={item['type']})")
            if item["variability"] != "parameter" or item["isValueChangeable"] != "true":
                errors.append(f"override {name}: compiled parameter is not runtime-changeable "
                              f"(variability={item['variability']}, isValueChangeable={item['isValueChangeable']})")
    except (OSError, ET.ParseError, ValueError) as error:
        errors.append(f"override metadata: {error}")

    # CSV omits parameters. Read the runtime's final parameter output instead.
    # Missing/ambiguous readback is a failure, never an inferred applied value.
    lines = [line for line in messages.splitlines() if line.startswith("time=")]
    try:
        if len(lines) != 1:
            raise ValueError("missing or ambiguous runtime parameter readback")
        evidence["readback_line"] = lines[0]
        pairs = [field.split("=", 1) for field in lines[0].split(",")]
        actual = dict(pairs)
        if len(actual) != len(pairs) or set(actual) != {"time", *overrides}:
            raise ValueError("incomplete or ambiguous runtime parameter readback")
        if not math.isfinite(float(actual["time"])) or abs(float(actual["time"]) - stop) > 1e-8:
            raise ValueError("runtime parameter readback has wrong final time")
        for name, requested in overrides.items():
            value = float(actual[name])
            if not math.isfinite(value):
                raise ValueError(f"nonfinite runtime readback for override {name}")
            item = evidence["parameters"].setdefault(name, {})
            item["effective_value"] = value
            item["readback_source"] = "simulation.messages (-output)"
            if value != requested:
                errors.append(f"override {name}: requested {requested!r}, effective runtime value {value!r}")
    except (ValueError, KeyError) as error:
        errors.append(f"override readback: {error}")
    evidence["validated"] = not errors
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("model")
    parser.add_argument("--stop", type=float, default=1.0)
    parser.add_argument("--intervals", type=int, default=1000)
    parser.add_argument("--override", action="append", default=[], metavar="NAME=NUMBER")
    parser.add_argument("--fmu", action="store_true", help="also export FMI 2.0 Model Exchange, defaults only")
    parser.add_argument("--output-root", type=Path, default=ROOT / "artifacts/smoke/runs")
    args = parser.parse_args()
    source = args.source.resolve()
    output_root = args.output_root.resolve()
    if not source.is_relative_to(ROOT) or source.suffix != ".mo" or not source.is_file():
        parser.error("source must be an existing .mo inside this workspace")
    if not output_root.is_relative_to(ROOT / "artifacts/smoke"):
        parser.error("output root must be under artifacts/smoke")
    if not NAME.fullmatch(args.model):
        parser.error("invalid qualified Modelica class name")
    if not math.isfinite(args.stop) or args.stop <= 0 or not 1 <= args.intervals <= 1000000:
        parser.error("invalid simulation horizon or interval count")
    if args.fmu and args.override:
        parser.error("FMU export uses model defaults; --fmu cannot accompany runtime overrides")
    overrides = {}
    for item in args.override:
        try:
            key, value = item.split("=", 1)
            number = float(value)
            if not NAME.fullmatch(key) or not math.isfinite(number) or key in overrides:
                raise ValueError()
            overrides[key] = number
        except ValueError:
            parser.error("overrides require unique qualified NAME=finite-number")
    run = output_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ-") + uuid.uuid4().hex[:10])
    run.mkdir(parents=True, exist_ok=False)
    source_bytes = source.read_bytes()
    snapshot = run / "model.mo"
    snapshot.write_bytes(source_bytes)
    started_ns = time.time_ns()
    report = {"status": "FAIL", "started_utc": datetime.now(timezone.utc).isoformat(),
              "started_ns": started_ns, "source": str(source), "model": args.model,
              "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "snapshot": str(snapshot), "run_dir": str(run), "overrides": overrides,
              "stop": args.stop, "intervals": args.intervals, "tolerance": 1e-8,
              "versions": {}, "commands": []}
    omc = None
    try:
        from OMPython import OMCSessionLocal
        report["versions"]["OMPython"] = importlib.metadata.version("OMPython")
        omc = OMCSessionLocal(timeout=120)

        def command(expression):
            entry = {"expression": expression}
            report["commands"].append(entry)
            try:
                value = omc.sendExpression(expression)
                entry["response"] = value
                return value
            except Exception as error:
                # OMPython 4.1 consumes getMessagesStringInternal itself. Retain
                # its exception: a subsequent getErrorString can be empty.
                entry["exception"] = f"{type(error).__name__}: {error}"
                raise
            finally:
                entry["getErrorString_raw"] = omc.sendExpression("getErrorString()", parsed=False, raise_on_error=False)
                entry["diagnostics"] = entry.get("exception", "") + "\n" + entry["getErrorString_raw"]
                with (run / "transcript.jsonl").open("a") as log:
                    log.write(json.dumps(entry, default=str) + "\n")

        report["versions"]["OpenModelica"] = command("getVersion()")
        if command('loadModel(Modelica, {"4.1.0"}, requireExactVersion=true)') is not True:
            raise ValueError("failed to load exact Modelica 4.1.0")
        report["versions"]["Modelica"] = command("getVersion(Modelica)")
        if report["versions"]["Modelica"] != "4.1.0":
            raise ValueError("wrong Modelica version")
        command("cd(" + json.dumps(str(run)) + ")")
        if command("loadFile(" + json.dumps(str(snapshot)) + ")") is not True:
            raise ValueError("loadFile rejected model; see transcript.jsonl")
        check = command("checkModel(" + args.model + ")")
        report["check"] = check
        if not isinstance(check, str) or "completed successfully" not in check:
            raise ValueError("checkModel failed; see transcript.jsonl")
        parameters = command("getParameterNames(" + args.model + ")")
        unknown = sorted(set(overrides) - set(parameters or []))
        if unknown:
            raise ValueError("unknown parameter override: " + ", ".join(unknown) + "; only top-level parameters are supported")
        flags = ("-override=" + ",".join(k + "=" + repr(v) for k, v in overrides.items())
                 + " -output=" + ",".join(overrides)) if overrides else ""
        expr = (f'simulate({args.model}, startTime=0, stopTime={args.stop!r}, '
                f'numberOfIntervals={args.intervals}, tolerance=1e-8, method="dassl", '
                'outputFormat="csv", fileNamePrefix="result", simflags=' + json.dumps(flags) + ')')
        result = command(expr)
        report["simulation"] = result
        if not isinstance(result, dict) or not result.get("resultFile"):
            raise ValueError("simulate returned no result file; see transcript.jsonl")
        result_path = Path(result["resultFile"]).resolve()
        if result_path != run / "result_res.csv":
            raise ValueError("unexpected simulation result path")
        report["data"] = finite_csv(result_path, started_ns, 0, args.stop)
        report["result_file"] = str(result_path)
        report["result_sha256"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
        if overrides:
            evidence = override_evidence(run, overrides, started_ns, args.stop,
                                         str(result.get("messages", "")), report["commands"][-1]["diagnostics"])
            report["override_validation"] = evidence
            if not evidence["validated"]:
                raise ValueError("runtime override validation failed: " + "\n".join(evidence["errors"]))
        if args.fmu:
            exported = command(f'buildModelFMU({args.model}, version="2.0", fmuType="me", fileNamePrefix="export")')
            if not isinstance(exported, str) or not exported:
                raise ValueError("FMU export returned no file")
            fmu_path = Path(exported).resolve()
            if fmu_path != run / "export.fmu" or not fmu_path.is_file() or fmu_path.stat().st_mtime_ns < started_ns:
                raise ValueError("missing, stale or unexpected FMU path")
            with zipfile.ZipFile(fmu_path) as archive:
                if archive.testzip() is not None or not any(n.endswith(".so") for n in archive.namelist()):
                    raise ValueError("invalid FMU archive or missing Linux shared library")
                description = ET.fromstring(archive.read("modelDescription.xml"))
                if description.get("fmiVersion") != "2.0" or description.find("ModelExchange") is None:
                    raise ValueError("wrong FMI version or kind")
            report["fmu"] = {"path": str(fmu_path), "fmi_version": "2.0", "kind": "ModelExchange",
                             "sha256": hashlib.sha256(fmu_path.read_bytes()).hexdigest(),
                             "validation": "archive CRC, XML metadata, Linux binary presence; NOT importer simulation"}
        if source.read_bytes() != source_bytes:
            raise ValueError("source changed during execution")
        report["status"] = "PASS"
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        if omc is not None:
            try:
                (run / "omc.log").write_text(omc.get_log())
                omc.sendExpression("quit()", raise_on_error=False)
            except Exception as error:
                report["shutdown_diagnostic"] = str(error)
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (run / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(run / "report.json")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
