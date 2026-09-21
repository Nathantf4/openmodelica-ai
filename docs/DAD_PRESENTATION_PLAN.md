# Dad presentation — next build and rehearsal

Status: **technical preflight complete with Astra**. The golden model, measured before/after comparison, visible seeded-error repair and portable pack are built and tested. See `DAD_PRESENTATION.md` for the operator run-of-show. The actual presentation with dad remains to be scheduled/rehearsed as a meeting.

## What he should see

One public Modelica Standard Library example, developed and improved in front of him: plain-English requirements → editable model/script → real compiler validation → measured response → retune.

Use a drive-style speed PI loop, not a tour of the corpus or infrastructure:

- Rotational inertia `J=0.2 kg.m²`, viscous damping `d=0.1 N.m.s/rad`.
- MSL `LimPID`, explicitly configured as `SimpleController.PI`.
- Torque limited to ±5 N.m; controller output limits match the actuator limits.
- Speed setpoint changes from 0 to 10 rad/s at t=0.5 s.
- Simulate to t=3 s. Plot reference and speed together, torque on its own correctly labelled axis.
- Retune `k` and `Ti` without changing the plant. Target overshoot strictly below 10% and entry into the ±2% band by absolute simulation time t=2 s, remaining in the band through t=3 s. This is a finite-horizon result, not an infinite-time guarantee.
- Report gain pairs and IAE over the same declared time interval. Verify saturation actually occurs before describing anti-windup behavior; saturation alone does not prove comparative benefit from anti-windup.

## Roughly 12-minute run-of-show

1. **Frame the task.** “You asked whether the agent could write OpenModelica scripts. This is a public textbook-style stand-in, with no work data.”
2. **Generate and run.** Give Astra the frozen English specification, show the saved `.mo`/`.mos`, actual check/simulation and the first response plot.
3. **Repair.** Show an actual diagnostic and correction. If deliberately seeding an error, label it as deliberate; do not present a rehearsed/scripted fix as a spontaneous model mistake.
4. **Retune.** Keep the plant fixed, change only controller gains, resimulate and compare measured response and limits.
5. **Hand it over.** Give him a portable example folder and ask which public toy structure would be useful next. Do not request proprietary files, traces or site diagrams.

## Build order and completion gates

1. Ground exact classes/connectors with the local corpus and live compiler reflection. Existing `artifacts/speed-pi-grounding.json` is a starting reference, not proof a PID model exists.
2. Create the golden model and standalone script under `examples/pid_speed/`, with a usable native OMEdit diagram. Add tests before implementation; require fresh checkModel/simulate, finite data, units/initial-state checks and stated saturation constraints.
3. Establish a visibly poorer baseline and a retuned case using real simulation, not chosen-looking plots. The retuned case must meet the above measured targets. Preserve both results, source identity and effective gain readback.
4. Prepare a labelled defective copy and a real compiler-error/repair rehearsal. Keep it separate from the golden source.
5. Write `docs/DAD_PRESENTATION.md` with frozen prompts, exact launch/run commands, native OMEdit clicks, claims/limitations and fallback sequence.
6. Package `.mo`, relative-path `.mos`, two CSVs, two PNGs, prompts and a short README. Test the package from an extracted folder, without relying on this project's absolute paths. Do not include the private corpus.
7. Rehearse the complete sequence using Astra. Keep a saved, verified golden model and plots ready if live generation or connectivity fails.

## Presentation boundaries

BouncingBall is only an off-screen preflight. No three-phase network, FMU export, ETAP-replacement claim, quant corpus, neural controller or proprietary employer inputs. The **OpenModelica — Hermes Shared** GUI is now controlled by `omedit-desktop` MCP and is the preferred viewing surface. The original native GUI and headless `omedit` instance remain separate alternatives. Compiler success is not engineering certification.

## Readiness labels

- **Foundation:** verified.
- **PI golden model, gain comparison, presentation guide and portable pack:** built and verified; ZIP is `deliverables/dad-speed-pi.zip`.
- **Astra technical rehearsal:** performed in the shared MCP window, including an explicitly seeded compiler failure and repair. Full integration: 65 tests passed.
- **Presentation with dad:** not yet held. Hermes operates; Nathan introduces and asks questions.
