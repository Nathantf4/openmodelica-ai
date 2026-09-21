# Induction-machine EMT base

`examples/emt_base_machine/` is the source of truth for the editable take-home `deliverables/emt-base-machine.zip`. It contains two self-contained MSL 4.1.0 models: direct-on-line induction-machine start through a short RL line, and the same model with a three-phase bolted terminal fault. The top-level parameter dialog exposes supply, line, inertia, quadratic load, machine data and fault timing. Open the `.mo` files in OMEdit; `.mos` files are batch scripts.

Instantaneous stator phases and rotor dq dynamics represent electrical switching and machine transients with a 100 microsecond output interval. This is a reusable illustrative base model, not a plant twin or PSCAD/EMTP/ETAP replacement. It has no travelling-wave line, frequency-dependent line, arc, converter switching, protection or certification scope. Zero-flux/standstill initialization and line-current initialization are explicit; compiler initialization warnings are retained. No GUI or MCP operation was used for this lane. Ideal fault interruption produces an approximately 327 MV clearing-voltage artifact because the circuit has no arc or surge-limiting capacitance; the raw value is retained and disclosed, and cannot support an insulation/surge study.

The host harness `scripts/emt_base.py` executes byte-identical evidence copies of the existing checked runner in fresh artifact workspaces, preserving its source/output boundary and runtime override gates. It does not modify or fork the runner. Independent Python complex arithmetic checks the machine nominal point and actual quadratic-load operating point; fault checks use measured voltage, phase RMS currents, KCL, speed and CSV switch transitions. Two overrides and an intentional missing class exercise the failure/readback paths. Both package scripts are executed from fresh copies; the ZIP is extracted and replayed natively.

Verification block and exact final artifact paths are recorded in `artifacts/emt-base/VERIFICATION.md` and `FINAL_RESULT.md`. The initial RED log is `artifacts/emt-base/tdd/01-red.log`; final GREEN log is `artifacts/emt-base/tdd/03-green-final.log`.

**Full-regression limitation:** all 73 tests (65 existing + 8 new) collect, but the requested full suite cannot run within the dispatch's hard restrictions: four existing tests touch the two protected OMEdit containers, and existing tests/acquisition write outside the lane. No approval overriding those restrictions has arrived. `artifacts/emt-base/full-tests.log` records NOT RUN, not a regression pass. This prevents an all-requirements-complete claim even if the package's numerical and replay checks pass.

## Verification block

**5 take-home model/script files → 4 passed, 1 deliberate fail; 10 fresh finite CSVs in this canonical run; ZIP replay PASS; OMPython replay PASS; 8/8 new EMT tests passed. Full suite: NOT RUN, 73 collected (65 + 8), not 73 passed.**

Canonical run: `artifacts/emt-base/runs/20260921T204034Z-d753ff95/summary.json`. Archive hashes/member list: `artifacts/emt-base/runs/20260921T204034Z-d753ff95/zip-manifest.json`. ZIP: `deliverables/emt-base-machine.zip`. All measured A–F values, timings and exact CSV/report paths are in `artifacts/emt-base/VERIFICATION.md`.
