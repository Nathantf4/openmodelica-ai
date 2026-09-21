# First five minutes in OMEdit

**For learning together with Hermes, use the new “OpenModelica — Hermes Shared” launcher.** Its visible window is controlled by `omedit-desktop` MCP, and it already has an interactive `InertiaStep` copy, diagram and speed plot. You do not need to reopen files to use that loaded example. See `SHARED_DESKTOP.md`. The instructions below also apply to the independent native application.

## Which files to open

| File | Purpose | In OMEdit |
|---|---|---|
| `model.mo` | Modelica model/components/equations | Open as a model, then simulate |
| `run.mos` | Compiler commands to load/check/simulate | Opens as text; opening it does **not** execute it |
| `parameters.mos` | Script for baseline and changed-parameter simulations | Automation script, not a second model |
| `.csv` / `.mat` | Simulation results | Open as result files for plotting |

For learning the GUI, ignore the `.mos` files initially. **File → Open Directory** is a text-browsing feature; it is not equivalent to loading all models for simulation.

## Open the inertia example

1. Dismiss any duplicate-loading dialog with **OK**. Do not delete files on disk.
2. Choose **File → Open Model/Library File(s)** and open:
   `/home/nathan/openmodelica-ai/examples/inertia_step/model.mo`
3. In the **Libraries** pane, find and double-click **InertiaStep**. This is the class name declared inside `model.mo`. If it is already listed, select that existing entry instead of opening the file again.
4. Use **Text** view to inspect the source. These initial smoke models are code-first; their diagram layout has not been prepared as a polished presentation.
5. With InertiaStep active, choose **Simulation → Simulate**. Its experiment annotation sets the stop time to 1 second.
6. After a successful run, use the **Variables** browser and tick **omega** to plot angular velocity. Tick **angle** separately if desired. They have different units.

This model applies a torque step at 0.1 seconds to an initially stationary frictionless inertia. The checked baseline ends near 9 rad/s at 1 second. It is a simple rotational example, not a full electric-motor model.

## The confusing “Redefining class(es) parameters.mos” dialog

In OMEdit 1.27.1, non-model files are opened through `openTextFile`. When the same absolute file path is already loaded, this code reuses the generic “redefining classes” dialog—even though the item is just a script opened as text. Use the existing item rather than reopening it. This message is not a compiler or physics-validation failure.

For actual models, a redefinition message naming `InertiaStep` or `RLStep` similarly means that class is already in the session. Select the existing class. Do not load both the normal `RLStep` example and the deliberately defective `seeded_defect` copy into the same session: they intentionally share a class name.

Source verification: pinned `OMEdit/OMEditLIB/Modeling/LibraryTreeWidget.cpp`, `openFile` lines 3964–3973 and `openTextFile` lines 4171–4188.

## When you want automation

Use the checked runner/smoke commands in `docs/SMOKE.md`, not the GUI Open action on a `.mos`. Our `.mos` files expect `model.mo` in their current working directory, so copy the pair into a fresh artifact directory as documented rather than invoking a script from an arbitrary directory.

The visible native OMEdit and Hermes's isolated headless OMEdit are separate. Saved files can be exchanged; unsaved edits and loaded models are not automatically synchronized.
