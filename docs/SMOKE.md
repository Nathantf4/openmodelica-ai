# Compiler-driven smoke suite

Latest parent integration verification after the review fixes: **59 tests passed** across runtime, corpus, research, native desktop, MCP and smoke checks (`artifacts/post-review-all-tests.log`). The current fresh smoke-summary path is recorded in `artifacts/post-review-smoke-run.log`. The smoke-only post-fix run passed **27 tests** (`artifacts/override-fix/04-smoke-regression.log`). Earlier checkpoint counts/evidence below are preserved as historical runs, not the latest total.

## Verified result

Run from `/home/nathan/openmodelica-ai`:

```bash
.venv/bin/python scripts/smoke.py
.venv/bin/pytest tests/test_smoke_models.py tests/test_smoke_runner.py -q
```

The recorded run passed **six ordered cases**, using **OpenModelica 1.27.1, OMPython 4.1.0 and Modelica 4.1.0**. The regression run passed **17 tests**. Both ran after the wrapper was tightened to mount project code/examples/repos read-only, with only `runtime/` and `artifacts/` writable. No example directory needs to be writable inside the compiler container.

- Full evidence: [`../artifacts/smoke/suite-20260921T035437.055841Z-f21b7b7d/summary.json`](../artifacts/smoke/suite-20260921T035437.055841Z-f21b7b7d/summary.json).
- Test output: [`../artifacts/smoke/final-pytest.log`](../artifacts/smoke/final-pytest.log).
- Vertical RED→GREEN development logs: [`../artifacts/smoke/tdd/`](../artifacts/smoke/tdd/). The first repair attempt failed because OMPython consumed diagnostics; that failed `06-repair-green.log` is deliberately retained beside the corrected `06-repair-green-2.log`.
- Repeated runs create new timestamp/UUID directories; old compiler files, logs, results and plots are not deleted.

| Case | Actual maximum absolute error / observation | Acceptance threshold |
|---|---:|---:|
| Shipped BouncingBall ballistic height | 7.49e-16 m | 2e-5 m |
| First rebound restitution ratio | 0.0 error from 0.7 | 2e-3 |
| RL current | 1.07e-7 A | 2e-5 A |
| RL current derivative, excluding step instant | 4.30e-7 A/s | 2e-4 A/s |
| Inertia angular velocity | 1.10e-11 rad/s | 2e-5 rad/s |
| Three-phase current, full transient reference | 4.72e-7 A | 2e-4 A |
| Three-phase sum of currents | 1.07e-13 A | 1e-7 A |
| Three-phase connection KCL residual | 0 A | 1e-7 A |
| Three-phase source voltage reference | 4.58e-12 V | 1e-7 V |

These are toy-model numerical checks, not engineering certification. No power-system, protection, arc-flash, cable-sizing or real-plant suitability claim is made. This does not replace ETAP, SKM, PSCAD or other specialist engineering studies.

## Models and exact checks

Each model has a `model.mo` and `run.mos` under `examples/`. Every positive pair is actually executed via `omc`, then independently executed through the shared **OMCSessionLocal** runner. The host compares both numerical results with analytical expectations. Plots use host matplotlib/Agg; no GUI or OMEdit is required.

1. **`bouncing_ball`** — unmodified shipped `OMCompiler/Examples/BouncingBall.mo` from OpenModelica v1.27.1. Source provenance and full upstream licensing are retained in that directory. Before the first impact: `h=1-g*t²/2`, `v=-g*t`; first impact at `sqrt(2/g)` and immediate post/pre speed ratio `e=0.7`. The plot shows height and velocity; the height reference is only intended for the first ballistic arc.
2. **`rl_step`** — MSL `Modelica.Electrical.Analog.Sources.StepVoltage`, `Basic.Resistor`, `Basic.Inductor`, `Basic.Ground`. Defaults: `R=2 Ω`, `L=0.5 H`, `V=10 V`, `ts=0.1 s`, initially zero current. For `t>=ts`, `i=V/R*(1-exp(-R/L*(t-ts)))` and `di=V/L*exp(-R/L*(t-ts))`; zero beforehand. The exact discontinuity and its duplicate event rows are excluded only from the derivative comparison (`abs(t-ts)>1e-7`). Plots explicitly show **i(t)** and **der(i)**.
3. **`inertia_step`** — MSL `Modelica.Blocks.Sources.Step`, `Modelica.Mechanics.Rotational.Sources.Torque`, and `Components.Inertia`. Defaults: `J=0.2 kg.m²`, `tau=2 N.m`, `ts=0.1 s`, fixed zero angle/speed, no drag. `omega=tau/J*max(t-ts,0)` and `angle=tau/(2J)*max(t-ts,0)²`. This is a simple inertia example, **not** a DC-machine model.
4. **`parameters`** — reruns the same RL and inertia source bytes with real simulation overrides. RL: `R=4,L=0.25,V=12`; final current changes from 4.99749771 A to 3.00000000 A. Inertia: `J=0.4,tau=3`; final speed changes from 9.0 to 6.75 rad/s. Both changed trajectories match their changed analytical references. The corresponding `parameters.mos` files also run baseline and changed simulations. The suite checks equal source hashes, different run directories, physical differences and changed-reference agreement.
5. **`three_phase`** — balanced MSL Polyphase sine source → series polyphase resistor/inductor line → resistive load; source and load grounded-star neutrals. `Vpeak=230*sqrt(2) V`, `f=50 Hz`, `Rline=1 Ω`, `Lline=0.01 H`, `Rload=9 Ω` per phase, zero initial currents. Phases are `0,-2*pi/3,-4*pi/3`. Let `R=Rline+Rload`, `w=2*pi*f`, `theta=atan(w*L/R)`, `Z=sqrt(R²+(wL)²)`. Each phase is checked against `Vpeak/Z * (sin(w*t+phase-theta)-sin(phase-theta)*exp(-R*t/L))`, including startup, rather than incorrectly assuming steady state from time zero. Source waveforms, current balance and connection KCL are checked independently. Expected impedance is 10.48187027 Ω and steady peak current 31.03159178 A.
6. **`repair`** — see below.

The default suite orders the three-phase case **after** bouncing, RL, inertia and parameter reruns. `--only bouncing|rl|inertia|parameters|three_phase|repair` is available for targeted reruns after the prerequisite toolchain is known good.

## Failure and repair proof

`examples/seeded_defect/model.mo` intentionally misspells `Modelica.Electrical.Analog.Sources.StepVoltage` as `StepVoltag`. This is an **explicitly seeded defect**, not evidence that a separate autonomous LLM found and repaired a spontaneous error. No external model calls were used; the drafting agent used the real compiler as the oracle.

```bash
.venv/bin/python scripts/smoke.py --only repair
# Direct negative check: EXPECT exit 1 and a FAIL report path.
bin/om python3 scripts/run_model.py examples/seeded_defect/model.mo RLStep --stop 2
```

The repair scenario first compiles a valid candidate, overwrites that candidate path with the seeded defect, observes a fresh failure, corrects the class name, and compiles/simulates again. Immutable per-run snapshots and source hashes retain each version. It checks that the failed run produced no result and that the prior valid result is unchanged. The repaired current and derivative pass the same RL oracle.

Actual diagnostic:

```text
[translation:error:3] .../model.mo:false:7:3:7:74
Class Modelica.Electrical.Analog.Sources.StepVoltag not found in scope RLStep.
```

**The deliberately invalid raw `.mos` exited 0** while emitting this compiler error and creating no result. This is why the suite never treats process exit alone as success.

OMPython 4.1 calls `getMessagesStringInternal()` internally and consumes its diagnostics. A subsequent `getErrorString()` may legitimately be empty. The runner retains the full **OMSessionException** (including file/line/location), and also records `getErrorString(parsed=False)` separately. Using only `raise_on_error=False` plus a later `getErrorString` would lose the actionable diagnostic; the preserved failed development run demonstrated this.

## Shared runner for future self-contained local models

```bash
bin/om python3 scripts/run_model.py examples/rl_step/model.mo RLStep \
  --stop 2 --intervals 2000 --override R=4 --override L=0.25 --override V=12
```

Run this **inside the pinned container**, not host Python: the host environment intentionally does not supply OMPython. The host `.venv` is used for pytest, numpy and matplotlib.

The CLI accepts an existing `.mo` inside this workspace, a validated qualified class identifier, a finite positive horizon, bounded intervals, and finite numeric **top-level scalar Real parameter** overrides. It rejects malformed/injected identifiers, duplicate overrides, nonfinite values and unknown parameter names before simulation. A real negative control demonstrated that OMC silently ignored an unknown override and returned a seemingly successful simulation; the runner checks `getParameterNames` explicitly. This numeric interface does **not** support Integer, Boolean, String, enumeration, array or nested-component overrides; it does not evaluate arbitrary Modelica expressions.

A declared parameter name is not proof of runtime applicability. After simulation, every requested override must also pass all three gates:

- Fresh `result_init.xml` must identify a scalar Real parameter with `isValueChangeable="true"`. Missing/ambiguous metadata and final, structural, evaluated or otherwise nonchangeable quantities fail closed.
- Preserved simulation/compiler diagnostics must not report rejected, unknown or unparsed overrides. Other warnings are **not** blanket failures: real zero/small-value override tests still pass with the runtime's numerical-caution warning.
- The same simulation is run with `-output=NAME,...`; its final-time parameter readback must be complete, unambiguous, finite and exactly equal to the requested floating-point values. CSV does not contain parameters, and the initialization XML contains **compiled defaults**, not effective override values. Neither the requested flags nor XML defaults are used as invented readback.

`report.overrides` remains the **requested** mapping. `report.override_validation` retains the metadata path/hash, compiled type/changeability/default, actual `effective_value` with its readback source, raw readback line, validation result and errors. Validation happens after simulation, so a rejected override can leave a fresh, finite CSV; that file is retained as failure evidence and does **not** earn PASS.

Real-compiler regressions cover both `final parameter Real gain=1` and `parameter Real gain=1 annotation(Evaluate=true)` with `--override gain=2`. Both now return nonzero/FAIL, retain `It is not possible to override the following quantity: gain`, and record actual `gain=1` rather than claiming `gain=2`. Ordinary R/L overrides retain positive runtime-readback and analytical-trajectory checks. RED/GREEN logs and the independent review reproducer's post-fix evidence are under [`../artifacts/override-fix/`](../artifacts/override-fix/); original review evidence is preserved separately under `artifacts/review/`.

Each invocation creates a new directory under `artifacts/smoke/` containing:

- original input snapshot; SHA-256 of input, runner and result;
- start/end UTC timestamps, requested class/horizon/tolerance/overrides, actual tool versions;
- expression/response/diagnostic transcript JSONL and full JSON report;
- OMC log, generated C/build products, simulation CSV;
- optional FMU.

Success requires loadModel/loadFile success, explicit `checkModel` success, nonempty simulate result, exact expected new result path, a fresh result timestamp, all numeric cells finite, nondecreasing simulation time, and the complete requested time horizon. Source changes during a run fail the run. Reports return nonzero on failure. Historical PASS reports are historical evidence only; **rerun after any source or parameter change**. The analytical harness adds physics checks; the general runner alone does not certify arbitrary model physics.

The runner is for **trusted, self-contained** Modelica input. Copying a single `.mo` into a fresh directory does not bundle a multi-file package or relative external resources; adapt the packaging deliberately for such tasks. Modelica can call external C/functions and file APIs. Numeric argument validation is not a security sandbox. The pinned wrapper denies networking and host-home access, mounts code read-only, and limits resources, but the intentionally writable project `runtime/` and `artifacts/` remain accessible to executed code.

## Standalone `.mos` execution without writing sources

Do **not** execute from `examples/`. The scripts use `loadFile("model.mo")` and write into their current directory. Copy the pair into a new artifact directory first (the harness does this automatically):

```bash
cd /home/nathan/openmodelica-ai
RUN="$(.venv/bin/python -c 'from pathlib import Path; import tempfile; p=Path("artifacts/smoke").resolve(); p.mkdir(parents=True,exist_ok=True); print(tempfile.mkdtemp(prefix="manual-rl-",dir=p))')"
cp examples/rl_step/model.mo examples/rl_step/run.mos "$RUN/"
(cd "$RUN" && /home/nathan/openmodelica-ai/bin/om omc run.mos)
```

For repeatable checked execution, prefer `.venv/bin/python scripts/smoke.py --only rl`, which verifies fresh output and analytics rather than merely displaying raw OMC output. Matplotlib plots are produced by the host harness, not an interactive `plot()` invocation in the headless `.mos` file.

## Optional FMU export

```bash
bin/om python3 scripts/run_model.py examples/rl_step/model.mo RLStep --stop 2 --fmu
```

Actual export passed: FMI **2.0 Model Exchange**, ZIP CRC validation, `modelDescription.xml` version/type and Linux shared-library presence. Example evidence:

`artifacts/smoke/runner-tests/8c83bfb854fe41f798588cec3d9c1583/20260921T035655.171771Z-ee7cae97fe/export.fmu`

This validates export/archive structure only, **not** an FMI import/co-simulation run, portability to Windows, or engineering suitability. `--fmu` is incompatible with runtime `--override`: exported defaults must not be confused with simulation-only parameter flags.

## Reproducibility boundaries

Tests exercise real Docker/OMC/OMPython, not mocked compiler responses. Finite-data negative tests intentionally use tiny invalid CSV fixtures solely to test the validator; they are not simulation evidence. The suite tests NaN/±Infinity, stale files, incomplete/backward time, malformed overrides, ignored-parameter prevention, source-change invalidation, repair, parameter physics and optional export. Numerical results can differ slightly across compiler/platform revisions; compare against the documented tolerances, not exact CSV bytes. Keep prior evidence, and retain the full OMC diagnostic when iterating.
