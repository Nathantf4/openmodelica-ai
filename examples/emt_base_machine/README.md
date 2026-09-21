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

## Running on your own computer

### What you need

| Software | Version used to build this package | Why |
|---|---|---|
| OpenModelica (OMEdit + `omc`) | **1.27.1** | Opens, checks and simulates the `.mo` files. Any 1.24 or newer should work; 1.27.1 is what was verified. Windows/macOS/Linux installers: https://openmodelica.org/download/ |
| Modelica Standard Library (MSL) | **4.1.0** | The only library these models use. It ships **inside** OpenModelica ≥ 1.24; nothing separate to download. In OMEdit, File → System Libraries lists it; `Modelica` also auto-loads when you open a model that declares `uses(Modelica(version="4.1.0"))`, which these do. |
| Python 3.10+ with `OMPython` 4.1.0 | optional | Only for `Scripts/check_and_simulate.py`. Not needed for OMEdit or the `.mos` batch script. |

If OMEdit reports it cannot find `Modelica` 4.1.0: File → Manage Libraries → Install Library → pick `Modelica`, version `4.1.0`, then reopen the model. (Equivalent `omc` command: `installPackage(Modelica, "4.1.0", exactMatch=true)`.)

Linux notes: on Ubuntu/Debian follow the apt instructions on the download page (they add the OpenModelica repository, then `apt install openmodelica`), which installs `omc`, `omedit` and the library cache together. `omc` also pulls in a C compiler (clang) and CMake automatically — simulation compiles generated C code, so a compiler must be present. On Windows the installer bundles everything.

### Graphical (recommended)

1. Extract the ZIP anywhere writable (e.g. `Documents/emt-base-machine/`). Do not put it under the OpenModelica installation folder; OMEdit treats those as read-only system libraries.
2. OMEdit → File → Open Model/Library File(s) → `Models/EmtMachineBaseFault.mo` (or `EmtMachineBase.mo`).
3. Double-click the model in the Libraries browser (top-left) to see the diagram. Simulate (green arrow or Simulation → Simulate). Expect one "initial conditions are over specified … 1 initial equation is redundant" notice — this is documented above and is not an error.
4. Switch to Plotting and tick variables in the Variables browser (right side). Parameters you change in the Variables browser take effect with **Re-simulate**; parameters changed in the model's parameter dialog (Modeling view) take effect with **Simulate**.

### Batch: compiler only (no Python)

From a terminal, inside the extracted package root (the folder that contains `Models/`, `Scripts/`, `Fixtures/`, `Results/`):

```sh
omc Scripts/check_and_simulate.mos
```

`omc` must be on your PATH. Windows: `"C:\Program Files\OpenModelica1.27.1-64bit\bin\omc.exe" Scripts\check_and_simulate.mos` (adjust the path to your installation). The script prints `PASS:` / `FAIL:` / `EXPECTED_FAIL:` lines and writes CSVs into `Results/`. Expect about 10–20 s per model on a laptop.

### Batch: Python (optional)

```sh
python3 -m venv .venv               # Windows: py -3 -m venv .venv
. .venv/bin/activate                # Windows: .venv\Scripts\activate
pip install "OMPython==4.1.0"       # pulls numpy, psutil, pyparsing, pyzmq
python Scripts/check_and_simulate.py
```

`OMPython` finds `omc` through the `OPENMODELICAHOME` environment variable (set by the Windows installer) or through `omc` on your PATH. On Linux, if it cannot find it: `export OPENMODELICAHOME=/usr` for an apt installation. The script uses `OMCSessionLocal`, which exists from OMPython 4.1.0 onward; older OMPython versions will fail with an import error.

### What the batch scripts check

Both scripts load, check and simulate the good models, delete any prior expected result files, print explicit `PASS`/`FAIL` lines, and try the deliberate `Fixtures/BrokenMissingClass.mo` typo. Good CSVs go to `Results/`. The `.mos` gates the returned result path, runtime completion, final time and nonfinite text; the Python script additionally checks every numeric cell, file freshness, and writes `Results/verification.json`. A missing-class diagnostic and no broken-fixture CSV earn `EXPECTED_FAIL`. Raw `omc` can exit **0 on errors**; never use shell status as the success criterion. The CSV header can contain quoted matrix names when saving all internal variables: use a CSV-aware parser. The take-home scripts select the named plot signals for manageable output and compatibility with OMC's CSV reader.

### How this package was verified before sending

Independent of the scripts above, the originating environment re-ran both models through a checked runner (30 000 intervals over 3 s, tolerance 1e-8, validated parameter overrides with runtime readback) and compared the results against a separate complex-arithmetic equivalent-circuit calculation (not the model's own power-balance record): time-weighted phase RMS over complete cycles, measured CSV switch edges, Kirchhoff current sums, trajectory comparisons, plus a fresh-folder replay, a ZIP-extraction replay and an OMPython replay. That evidence (hashes, wall times, plots, per-run JSON) is kept with the originating project, not in this ZIP. `Results/` ships empty on purpose; everything in it is regenerated on your machine.

Version/provenance: built and verified against OpenModelica 1.27.1 with the MSL it ships (**4.1.0+maint.om**, which reports itself as 4.1.0). Wiring, machine modifiers and initialization are adapted from the MSL example `Modelica.Electrical.Machines.Examples.InductionMachines.IMC_DOL`; the nominal numbers quoted above come from the `IM_SquirrelCage` documentation table in that library. MSL is not bundled in this ZIP; your OpenModelica installation provides it.

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
