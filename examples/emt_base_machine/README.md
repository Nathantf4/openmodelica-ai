# Editable induction-machine EMT base

This electromagnetic transient model resolves winding and switching behavior on microsecond–millisecond timescales, including 50 Hz waveforms, while the 3 s run shows the slower electromechanical speed envelope. Output interval: 100 microseconds; DASSL uses adaptive internal steps.

Open the `.mo` in OMEdit; the `.mos` is batch text. Opening a `.mos` in OMEdit does not execute it. Open `Models/EmtMachineBase.mo` for the direct-on-line start or `Models/EmtMachineBaseFault.mo` for the same motor with one bolted three-phase terminal fault. Each file contains one independent top-level model and needs only Modelica Standard Library 4.1.0.

In OMEdit, open the model's parameter dialog, change a value, and Simulate. Start with **TLoad**, **JLoad**, and (in the fault model) **tClear**. `tFault` moves the fault; `tClear` is its duration, so clearing occurs at `tFault + tClear`. Try `JLoad=0.58` for a slower start or `TLoad=193.68` for a heavier load. Run through 3 s with interval 0.0001 s and tolerance 1e-6; extend StopTime when moving the fault later or increasing inertia.

| Top-level parameter | Default | Unit | Meaning |
|---|---:|---|---|
| VNominal | 100 | V RMS | Source line-to-neutral voltage; line-to-line RMS is sqrt(3) times this |
| fNominal | 50 | Hz | Source frequency |
| tStart | 0.1 | s | All three DOL contactor poles close |
| TLoad | 161.4 | N·m | Quadratic load torque magnitude at wLoad |
| wLoad | 150.84357 (1440.45 rpm) | rad/s | Load reference speed; dialog displays rev/min |
| JLoad | 0.29 | kg·m² | External load inertia, in addition to the default 0.29 rotor inertia |
| RLine | 0.005 | Ω/phase | Lumped series line resistance |
| LLine | 9.549296586e-5 | H/phase | Lumped series line inductance |
| XLine (final) | 0.03 at 50 Hz | Ω/phase | Derived 2·pi·fNominal·LLine; edit LLine to change it |
| imcData | MSL defaults | mixed SI | Expand this record to edit the machine's pole pairs, resistance, inductance, inertia and loss data |
| tFault (fault model) | 1.5 | s | Fault closes |
| tClear (fault model) | 0.1 | s | Duration before fault opens |
| RFault (fault model) | 1e-5 | Ω/phase | Small on-resistance, giving a bolted fault approximation |

`imcData.fsNominal` defines the frequency at which the machine's default inductances are specified. Changing source `fNominal` changes the operating frequency without automatically redesigning the machine. Temperature coefficients default to zero; operational stator and rotor temperatures are fixed at 293.15 K.

The supply is a balanced infinite bus with a grounded star neutral. The motor is **Y-connected with an isolated star point**, so each winding sees approximately the source's line-to-neutral voltage. This differs from the delta connection and voltage scaling in the MSL IMC_DOL template. The short line's 0.005+j0.03 Ω impedance keeps the default operating point close to the documented 100 A / 1440.45 rpm point, while limiting the fault current to about 3.29 kA. The illustrative 0.02+j0.15 Ω line would give about 112 A at constant 161.4 N·m and would fail this package's nominal-current tolerance. These line values describe an illustrative stiff supply, not a specified cable or installation.

The load is opposing quadratic torque: `TLoad*(w/wLoad)^2` for positive rotation, reversing sign for reverse rotation. Thus 161.4 N·m is its rating at wLoad; actual final torque is slightly lower when the line reduces speed. The model starts at standstill with zero angle, zero stator current and zero rotor current/flux, using the IMC_DOL initial equations. The fault variant also initializes all line currents to zero because the shunt adds independent line states. Small contactor off conductances (1e-5 S) regularize the open electrical network; leakage before tStart is about 1 mA. The DOL contactor has 1e-5 Ω on-resistance. The fault switch uses RFault on-resistance and 1e-5 S off-conductance. These are idealized switches, not arcs or protection devices. Retaining the required three zero stator-current equations in a balanced Y system produces a redundant-initial-equation compiler warning; the diagnostics are preserved.

The machine uses instantaneous phase-domain stator quantities and a rotor dq representation; it is not a fundamental-frequency phasor-only network. Plot phase-current DC offsets at switching, torque pulsations, speed dip and recovery. Default magnetics are linear, with no magnetic saturation or skin-effect model; optional MSL friction, core and stray-load losses default to zero. No travelling-wave / frequency-dependent line, no arc model, no converter switching. This is not PSCAD/EMTP/ETAP and is not a plant twin, protection study, arc-flash analysis or physical certification. Do not tune EMT results on a single pretty plot.

**Clearing-voltage limitation:** the measured ideal-switch opening event produces an approximately **327 MV** instantaneous terminal-magnitude spike. Interrupting inductive fault current into the 1e-5 S off-conductance, with no arc or surge-limiting capacitance, sets this nonphysical peak. It is retained in the CSV and plotted on a symlog voltage axis, not clipped or treated as an insulation/surge prediction. The fault-on RMS and speed checks do not validate that peak. Add an explicitly specified interruption/surge model before studying clearing overvoltage.

Useful plot variables (the batch CSVs keep these visible signals):

- `aimc.is[1]`, `aimc.is[2]`, `aimc.is[3]`: instantaneous winding currents, A.
- `currentRMS.I`: stator quasi-RMS current, A. It equals phase RMS in balanced sinusoidal steady state; transient magnitude is not a cycle RMS calculation.
- `vTerminal[1:3]`: phase-to-source-neutral terminal voltages, V; `terminalVRMS`: instantaneous three-phase magnitude, equal to phase RMS in balanced steady state.
- `aimc.wMechanical`: rad/s, displayUnit rev/min; `aimc.tauElectrical`: N·m.
- Fault model: `faultSwitch.i[1:3]`, `iSource[1:3]`, and `faultSwitch.control[1:3]`. Source currents are positive toward the line. Inspect 1.47–1.65 s to see the fault and clearing.

From the extracted package root:

```sh
omc Scripts/check_and_simulate.mos
# On the originating machine use omc-native for the native installation.
# With OMPython installed:
python3 Scripts/check_and_simulate.py
```

Both batch scripts load, check and simulate the good models, clear their prior expected result files, print explicit PASS/FAIL lines, and try the deliberate `Fixtures/BrokenMissingClass.mo` typo. Good CSVs go to `Results/`. The `.mos` gates the returned result path, runtime completion, final time and nonfinite text; the Python script additionally checks every numeric cell, file freshness, and writes `Results/verification.json`. A missing-class diagnostic and no broken-fixture CSV earn EXPECTED_FAIL. Raw `omc` can exit **0 on errors**; never use shell status as the success criterion. The CSV header can contain quoted matrix names when saving all internal variables: use a CSV-aware parser. The take-home scripts select the named plot signals for manageable output and compatibility with OMC's CSV reader.

Inside the originating project, the harness makes and runs fresh writable copies automatically:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/emt_base.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider tests/test_emt_base.py -q
```

For a manual isolated replay, change into a fresh copied package under `artifacts/emt-base/`, then run `/home/nathan/openmodelica-ai/bin/om python3 Scripts/check_and_simulate.py`. The examples tree is read-only inside `bin/om`.

The host harness runs the existing `scripts/run_model.py` through `bin/om python3`, with 30000 intervals over 3 s, validated scalar overrides and actual runtime readback. Because that runner only accepts `artifacts/smoke` relative to its own workspace, the harness places a **byte-identical copy** of the runner and model in a fresh workspace under `artifacts/emt-base/runs/`. It does not modify or fork the runner. The checked runner uses its existing stricter tolerance 1e-8. Host verification adds independent complex-arithmetic equivalent-circuit calculations (not `powerBalance`), time-weighted phase RMS measurements over complete cycles, measured CSV switch edges, KCL, trajectory comparisons, native folder and ZIP replay, and OMPython script replay. Evidence, hashes, wall times, plots and per-run JSON are retained outside this ZIP in `artifacts/emt-base/`; see `VERIFICATION.md` and `FINAL_RESULT.md` there. ZIP Results/ is empty.

Version/provenance: built against OpenModelica 1.27.1 and runtime MSL **4.1.0+maint.om** (reports 4.1.0; maintained commit 8df0769a9cee6ad04ddfff95faee64cd70f662ec). The upstream v4.1.0 checkout is reference data and is not claimed bit-identical. Wiring, machine modifiers and initialization are adapted from MSL `Modelica.Electrical.Machines.Examples.InductionMachines.IMC_DOL`; nominal numbers are in the installed `IM_SquirrelCage` documentation table. MSL is installed separately, not bundled. The generating session's selected model was preserved; no model-ranking claim is made.

MSL attribution for the adapted example structure:

```
BSD 3-Clause License

Copyright (c) 1998-2025, Modelica Association and contributors
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
