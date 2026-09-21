# Shared, desktop-visible OMEdit

Use the application launcher **OpenModelica — Hermes Shared**, or:

```sh
/home/nathan/openmodelica-ai/bin/omedit-desktop start
```

This opens a real OMEdit window on the local Wayland desktop. Hermes MCP server **`omedit-desktop`** controls this same application: loading, editing, checking, simulation, diagrams and plots are visible to both Nathan and Hermes. It is no longer necessary to carry saved files between the headless instance and a separate native viewer for this workflow.

## The three instances

| Launcher/tool | Instance |
|---|---|
| **OpenModelica — Hermes Shared** / `omedit-desktop` MCP | Visible shared window; use this for guided learning/demo |
| **OpenModelica OMEdit** / `OMEdit` | Original native application, independently usable; not connected to these MCP tools |
| `omedit` MCP / `bin/omedit-mcp` | Original headless isolated instance; retained for automation/tests |

The native window was not closed or reset. Its unsaved work was left untouched.

## Ready-to-use example

Writable interactive copy:

`/home/nathan/openmodelica-ai/artifacts/desktop-models/InertiaStep.mo`

The shared window has this class loaded, with a visible step → torque → inertia diagram and a successful simulation. The **omega** plot rises to approximately 9 rad/s at t=1 s. Choose **Modeling** at the bottom and open **InertiaStep** to see the diagram; **Plotting** returns to the result. A diagram heading says **Shared with Hermes**.

The canonical smoke example under `examples/inertia_step/` was not changed. Save interactive work under `artifacts/desktop-models/` (or another artifact subdirectory); source/code directories are read-only inside the container. Opening a `.mos` still does not execute it—see `GUI_QUICKSTART.md`.

MCP-generated source, diagram, plot and actual result-file reference are retained in `artifacts/desktop-models/mcp-evidence.json`. The actual desktop screenshot is `artifacts/omedit-desktop-window.png`.

## Lifecycle and boundary

```sh
bin/omedit-desktop health
bin/omedit-desktop status
bin/omedit-desktop logs
bin/omedit-desktop stop
hermes mcp test omedit-desktop
```

Closing this shared window terminates its GUI container. Reopen it with the launcher/start command before further MCP calls; save wanted edits first. Do not stop or restart it while Nathan is editing without checking for unsaved work.

The new image adds the Qt6 Wayland plugin to the already verified Qt6 OMEdit build. The launcher pins image ID `sha256:7ab058f3381bb93f1a94a64643d766e80d3c1b155eb8d595fbe0a6864cd1972a`. `docker/omedit-desktop/Dockerfile` records the build layer.

The container remains non-root, network-disabled, read-only at its root/code mounts, with 2 CPU / 3 GiB / 256-PID limits and no published ports. It shares **one Wayland display socket**, deliberately authorized for the visible window; no host home, Docker socket or entire desktop runtime directory is mounted. Rendering is software-based. The official MCP HTTP listener is only inside the container; Hermes reaches it over the local stdio adapter. Sampling and elicitation are disabled.

## Verification

`tests/test_omedit_desktop.py` matches the mapped desktop window's PID to the actual container OMEdit process, verifies network/port/mount boundaries, and initializes/calls the desktop-specific MCP adapter. The pre-existing headless MCP tests also pass. Actual Hermes tools performed load → layout/source update → checkModel → simulate → plot in the visible instance, and both the rendered diagram and desktop plot were inspected.

OMEdit placement lesson: code-first components without annotations can inherit `visible=false` when only coordinates are set. Set visibility explicitly and read back source/diagram; successful placement calls alone do not prove visible components.
