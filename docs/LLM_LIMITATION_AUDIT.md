# Extra verification: did we accept plausible but invalid Modelica?

## Verdict

**No unexpected syntax, connector, missing-library, compilation, simulation or tested-physics failures were found in the current working deliverables.** We verified executable artifacts rather than accepting chat output or an attractive plot.

## Fresh coverage

| Route | Observed result |
|---|---|
| Full integration/regression suite | **65 passed** on a fresh rerun |
| Independent native audit of saved files | **20 files:** 7 example `.mo`, 9 example `.mos`, 4 desktop `.mo`; **18 PASS, 2 EXPECTED_FAIL, 0 unexpected failures** |
| Independent native simulation data | **21 fresh CSVs**, checked for finite values, complete horizons, source/result identity and independent physics |
| Current shared-MCP memory | All **four live models** source-snapshotted, checked, resimulated and read back from new MAT files; source unchanged during each run |
| Actual take-home ZIP | CRC and source-byte checks; extracted into a fresh folder and run with native OMC, producing fresh passing baseline/retuned results |

Parent readback independently confirmed the reviewer file inventory, every current source hash, the saved result hashes, timestamps, all CSV cells/horizons, statuses and result counts. No source/config fixes were required by this additional audit.

## The expected failures are important

`examples/seeded_defect/model.mo` and its `run.mos` intentionally name nonexistent `StepVoltag`. Both fail with that precise compiler diagnostic and produce no result CSV—even though native OMC exits **0**. They are negative controls, not usable models or unexplained failures.

The saved/live `SpeedPIDemoDefect` is the **repaired** demonstration copy. It uses `controller.u_m`, and it passes checking, simulation and PI physics checks. A filename containing “Defect” is not itself an expected-failure contract.

## Beyond successful compilation

The independent reviewer did not import or run the builder's model/smoke/PI verifier. It used fresh native compilations and its own physical checks:

- RL exponential current, derivative and KVL.
- Torque/inertia angular speed and angle.
- BouncingBall ballistic motion and first restitution event.
- Three-phase startup response, source waveforms, KCL and phase balance.
- PI mechanics, integral dynamics, saturation and an independently implemented RK4 trajectory with step-halving checks.

Maximum independent PI speed discrepancy was approximately **6.61e-7 rad/s**. The before/after results reproduced about **21.707245% → 2.762491% overshoot** and **2.403 → 1.410 seconds absolute settling time**, with torque bounded at 5 N.m. Parent checks also verified the actual live MAT data using independent integral identities and effective gain values.

## What this says about the quoted LLM limitation

The concern is valid: a general-purpose model can invent Modelica classes, use wrong connectors or write plausible code that fails. Our acceptance path is **Astra → grounded library lookup → real OMC/MCP/OMPython feedback → fresh simulation → physical checks**, not plain-chat code delivery.

This does not show that Astra can never make a Modelica mistake. It shows the current working artifacts survive the checks designed to detect those mistakes. It also does not establish an Astra/Fable/Claude ranking: the extra reviewer used a separate Astra context and a native compiler/independent numerical route, not a different-model benchmark.

We do **not** claim a separate simulation after every historical keystroke, diagram placement or formatting edit. Current working revisions were explicitly checked and simulated, and this audit reverified both saved files and current GUI memory. New semantic or parameter changes still invalidate prior results and require fresh checks.

Compiler success and these toy-model checks are not industrial certification. Uncertain loads, noise, delays, real motor electrical dynamics and physical equipment were not qualified. The known nonfatal native libcurl packaging warning remains visible in logs.

## Evidence

- Independent report: `artifacts/llm-limit-audit/independent/REPORT.md`
- Independent manifest and per-file evidence: same directory, `manifest.json`, `all-evidence.json`, `physics-evidence.json`, `final-verification.json`.
- Parent cross-check: `artifacts/llm-limit-audit/parent/independent-readback.json`.
- Fresh regression log: `artifacts/llm-limit-audit/parent/full-tests.log`.
- Current live-state evidence directory: path in `artifacts/llm-limit-audit/parent/live-path.txt`.
- Actual ZIP extraction/native replay: path in `artifacts/llm-limit-audit/parent/portable-path.txt`.

Original review/source/delivery evidence was preserved. The shared window is left displaying the speed-PI comparison.
