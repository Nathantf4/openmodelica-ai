# Dad demo — Hermes operates, Nathan introduces

## Ready state

The technical preflight is complete with **Astra**. Use **OpenModelica — Hermes Shared** / `omedit-desktop` MCP; Nathan does not need to navigate the software. The golden model, measured before/after comparison, labelled seeded repair and portable take-home pack have all been executed. A presentation with dad has not happened yet.

- Diagram/model: `SpeedPIDemo` in the shared window.
- Before/after plot: `SpeedPIComparison`, variables `setpoint`, `baselineSpeed`, `retunedSpeed`.
- Torque plot: `baselineTorque`, `retunedTorque` in a separate plot (different units).
- Working GUI copies: `artifacts/desktop-models/`.
- Golden source pair: `examples/pid_speed/model.mo` + `run.mos`.
- Take-home ZIP: `/home/nathan/openmodelica-ai/deliverables/dad-speed-pi.zip`.
- Full evidence: `artifacts/dad-demo/presentation-v1/summary.json`, `live-repair.json`, `portable-verification.json`.

## What Nathan says

> You asked whether the agent could write OpenModelica scripts. This is a public textbook-style stand-in—not anything from work. I describe the system; Astra writes the model and script; the compiler checks it; then we inspect and improve the simulated response.

That is enough introduction. Nathan can ask questions or request a change; Hermes handles the application, code, diagnostics and plots.

## Run-of-show, roughly 12 minutes

1. **Show the physical model.** Hermes displays `SpeedPIDemo`'s diagram. Explain: a commanded speed feeds a PI controller, the controller requests torque, a rotational inertia moves against damping, and a speed sensor closes the loop. It is an ideal drive-style load, not a complete electrical motor/site model.
2. **Show generation and checking.** Use the frozen generation prompt below. For genuinely fresh live generation, use a new class name so it does not collide with the prepared golden. Show the actual `.mo`/`.mos`, checkModel, simulate and diagnostics. Do not conceal failure. If time/provider connectivity is a problem, say “this is the preflighted backup” and open the golden.
3. **Show the baseline.** Target is 10 rad/s, commanded at t=0.5 s. The blue `baselineSpeed` curve overshoots/rings. Show the torque plot: the actuator reaches its +5 N.m limit during startup.
4. **Retune without changing the plant.** Change only `k` and `Ti`, run again, and show the green `retunedSpeed` curve with the same red target. Explain that the gain selection tested four candidate pairs; it is not a globally optimal or robust industrial tuning claim.
5. **Show the repair capability.** Optional if a real error already occurred live. Otherwise say “I am deliberately introducing a wrong connector name.” In a separate copy, change `controller.u_m` to `controller.u_measure`; show the real compiler error, restore the verified connector, check and simulate again. Never call the seeded typo a spontaneous AI mistake.
6. **Hand over the pack and stop.** Ask which kind of public toy structure would be useful next. Do not ask for proprietary traces, one-lines or asset files.

## Measured comparison

Plant unchanged: J=0.2 kg.m², d=0.1 N.m.s/rad, torque bounds ±5 N.m, target 10 rad/s at t=0.5 s, stop t=3 s; tracking anti-windup Ni=0.9.

| Metric | Baseline | Retuned |
|---|---:|---:|
| k | 0.6 | 3.0 |
| Ti | 0.08 s | 0.6 s |
| Overshoot | 21.7072% | 2.7625% |
| Peak speed | 12.1707 rad/s | 10.2762 rad/s |
| Settling, absolute simulation time | 2.403 s | 1.410 s |
| Settling after the command step | 1.903 s | 0.910 s |
| IAE on 0–3 s | 3.30731 rad | 2.35980 rad |
| Peak absolute torque | 5 N.m | 5 N.m |

Settling means the first recorded sample after the last one outside 9.8–10.2 rad/s, remaining inside through t=3 s. It is a sampled finite-horizon measurement, not an infinite-time guarantee. Both source hashes match; effective gain readback was checked rather than inferred from requested override flags. An independently implemented mechanics/PI ODE agreed with both simulated speed traces to less than 1e-6 rad/s in these runs.

The model includes tracking anti-windup and actual saturation was observed. We did not run an anti-windup-disabled counterfactual, so do not claim this comparison isolates its benefit.

## Frozen prompts

**Generate**

> Use only Modelica Standard Library 4.1.0. Model rotational inertia J=0.2 kg.m² with viscous damping d=0.1 N.m.s/rad. Use LimPID explicitly as PI, initialized at zero speed and zero integral state. Track a speed step from 0 to 10 rad/s at t=0.5 s. Limit the controller/actuator torque to ±5 N.m. Write a self-contained .mo plus a .mos for 3 seconds, check and simulate with the actual compiler, retain diagnostics and fresh CSV output. Plot speed/reference and torque separately. This is a public toy, not employer data.

**Retune**

> Keep the plant and limits unchanged. Change only k and Ti. Achieve under 10% overshoot and enter the 2% speed band by absolute simulation time 2 s, remaining there through 3 s. Report both gain sets and IAE over 0–3 s. Verify actual effective parameter values and preserve both result sets.

## Operator actions

Hermes performs the actions, not Nathan. Before changing anything, read the current class source/state and preserve wanted edits.

- `omedit-desktop.classDiagram(SpeedPIDemo)` for the plant diagram. A newly loaded OMEdit model can render only its background annotations before a widget refresh. If components are absent despite `visible=true`, read its current source, reload that identical source through `setSourceCode`, then inspect the diagram again. Do not “fix” physical equations to fix rendering.
- `checkModel`, then `simulate`, then `plot` for a fresh model. A successful RPC or shell code alone is not the acceptance gate.
- The prepared `SpeedPIComparison` contains two independent copies of the exact same plant/controller structure, differing only in k/Ti. It provides a reproducible single plot for the before/after story; it is not pretending that one time trace was edited into another.
- Keep errors in the transcript. The visible seeded repair was actually executed and preserved in `live-repair.json`; the golden model was not damaged.
- Closing the shared window stops that GUI container. Start it with `bin/omedit-desktop start`, then load saved files if the classes are absent. Do not restart Nathan's separate native window or discard unsaved work.

## Rebuild and verification

```sh
cd /home/nathan/openmodelica-ai
.venv/bin/python scripts/pid_demo.py
.venv/bin/pytest tests/test_pid_demo.py tests/test_pid_delivery.py -q
```

The CLI prints a new summary path and creates a fresh pack. Output is append-only by fresh directory; it refuses to overwrite a selected existing output directory.

The final complete integration run passed **65 tests** (`artifacts/dad-demo/full-tests.log`). The actual delivered ZIP was extracted to a different folder and its relative-path `run.mos` was run with the native compiler; both fresh results passed their intended metrics and matched the retained traces. Modelica libraries are prerequisites on the receiving machine; no private corpus or MSL source dump is bundled.

**Do not claim:** industrial robustness, a full motor electrical model, engineering certification, globally optimal tuning, a spontaneous LLM failure when seeded, or replacement for specialist licensed studies. Noise, delay and uncertain loads were not modeled.
