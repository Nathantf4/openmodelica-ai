# End-goal context (not a new build gate)

Nathan supplied `/home/nathan/thoughts/shared/handoffs/openmodelica-ai/2026-09-20_23-12-20_dad-presentation.md` as **FYI about the eventual goal**, while asking to continue the foundation work. Its embedded “NOW” label does not override that qualification.

The intended next presentation is a short public-MSL drive-style speed-PI demo: English specification → saved model/script → real compiler diagnostics and repair → saturation/anti-windup → retuned trajectories. Use inertia and viscous damping, not a plant digital twin. BouncingBall stays an off-screen toolchain check. For the presentation, prefer the **OpenModelica — Hermes Shared** window controlled by `omedit-desktop` MCP; Nathan and Hermes now see the same edits and plots. The independently installed native OMEdit and older headless `omedit` MCP remain alternatives, not synchronized views.

Do not request proprietary employer data, ingest the quant corpus, or build a neural controller. Nathan has explicitly approved **Astra for the presentation**, superseding the imported handoff's Fable-only/on-screen restriction. Keep the current Astra session pinned; no Fable dependency or model switch is required. Preflight the actual presenting model and label its outputs honestly. The existing papers do not establish current-model rankings.

The presentation pack is now built and technically rehearsed with Astra: a compiling golden model, measured baseline/retuned gains, plots/CSVs, frozen prompts, a plainly labelled seeded-error repair, and a portable leave-behind. See `DAD_PRESENTATION.md` and `deliverables/dad-speed-pi.zip`. The original foundation checkpoint did not claim these; the later demo stage completed them. The actual meeting with dad has not happened.

Technical correction for future implementation: confirm `LimPID`'s real parameters/connector names through `lookup_class` and explicitly select `Modelica.Blocks.Types.SimpleController.PI`; do not rely solely on prose such as “Td=0 means PI”. Ensure the requested settling definition and time origin are explicit and verify output saturation actually occurs. Preserve controller/plant versions and both gain sets.
