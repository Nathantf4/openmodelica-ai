# Quant mathematics → OpenModelica and agent-driven ML

Status: conceptual transfer map grounded in local corpus notes and the current toy plant. This does not merge the corpora, train a model, add an ML controller, or establish suitability for real equipment. Quant files were consulted read-only.

## What transfers

| General mathematics | Engineering use | Relevant quant-corpus notes |
|---|---|---|
| State-space models and Bayesian/Kalman filtering | Estimate speed, unmeasured load torque or other states from noisy sensors; quantify uncertainty | `kalman-bayesian-filters.md`, `ts-classical-and-forecasting.md` |
| Regression, likelihoods and time-series identification | Estimate inertia/damping or an input–output model from applied torque and observed response | `ts-classical-and-forecasting.md`, `book-bishop-prml.md`, `book-mathematics-for-ml.md` |
| Stochastic processes and Monte Carlo | Stress controllers across uncertain parameters, load changes and plausible noise; measure failure distributions | `monte-carlo-methods.md`, `stochastic-processes.md` |
| Jacobians, eigenvalues and constrained optimization | Linearize nonlinear models locally, examine stability, and formulate LQR/MPC or bounded tuning problems | `book-mathematics-for-ml.md` |
| Gaussian-process/probabilistic regression | Learn a surrogate for simulation cost/performance, with uncertainty; use it to propose informative tuning experiments | `book-bishop-prml.md` |
| Out-of-sample validation and parameter robustness | Prefer broad good-performing gain regions; test unseen trajectories/scenarios instead of selecting one lucky simulation | `book-pardo-walk-forward.md`, `ts-classical-and-forecasting.md` |
| MDPs, Bellman equations and reinforcement learning | Eventually learn a simulated control policy when simpler PI/LQR/MPC methods are inadequate | `book-sutton-barto-reinforcement-learning.md` |

The corpus sheets live under `/home/nathan/quant/reference/distilled/`. Their trading-specific “use here” sections, old project references, numerical thresholds and calibration constants do not transfer automatically. These engineering applications are our synthesis, not claims that the finance authors validated this plant.

## A concrete bridge from our actual demo

The open-loop mechanical plant is:

```text
J * d(omega)/dt = applied_torque - d * omega
```

With the demo's J=0.2 and d=0.1, the verified continuous coefficients are:

```text
d(omega)/dt = -0.5 * omega + 5 * applied_torque
```

Under a **zero-order-held applied torque** with a 0.01-second sample period, the exact deterministic transition has coefficients (rounded here):

```text
omega[k+1] = 0.9950124792 * omega[k] + 0.0498752081 * applied_torque[k]
```

Add explicitly modeled process disturbance and sensor noise, and this becomes the same state-transition/observation form used in the Kalman corpus:

```text
x[k+1] = F*x[k] + B*u[k] + process_noise[k]
y[k]   = H*x[k] + measurement_noise[k]
```

Here the hidden quantity is physical speed/load, not a latent price or hedge ratio. Use actual applied torque after saturation, not an impossible requested torque. Noise covariances, sampling and delays must be engineering-calibrated; Gaussianity is an assumption, not a universal property of sensors.

The open-loop time constant is J/d=2 seconds. Its exponential decay half-life is approximately 1.386294 seconds. This shares the exponential-relaxation mathematics of OU mean reversion, but is **not** the PI closed-loop settling time and does not make a motor a financial price process.

Reproduction of the coefficients was run with Python:

```python
import math
J, d, dt = 0.2, 0.1, 0.01
A, B = -d/J, 1/J
F = math.exp(A*dt)
Bd = B*math.expm1(A*dt)/A
assert math.isclose((1-F)/Bd, d, rel_tol=1e-12)
assert math.isclose(-d*dt/math.log(F), J, rel_tol=1e-12)
```

### Source-verification caution

`pairs-stat-arb.md:268` describes lambda<0 but prints half-life as ln(2)/lambda. Under that convention the positive half-life is **-ln(2)/lambda**. The definition check exp(lambda*t_half)=0.5 confirms the sign. The quant note was not modified. This is a concrete reason to verify distilled formulas before making them load-bearing rather than bulk importing notes.

## Three separate meanings of “ML”

1. **LLM-assisted engineering — already present.** Astra interprets requirements, grounds library classes, writes models/scripts, operates MCP, reads diagnostics and explains results. Skills/retrieval do not retrain its model weights.
2. **ML-assisted experiments — a sensible next extension.** Python can fit parameters, a Gaussian-process surrogate or a residual model. An optimizer proposes the next simulation; the real simulator and held-out checks decide whether it works. Our present four-pair gain comparison was a bounded search, not a trained Bayesian optimizer.
3. **ML inside the control system — later and separate.** A learned estimator, surrogate or policy can become a model component only after appropriate integration and validation. A small regression or Kalman estimator is preferable to a neural controller unless complexity earns its place. RL remains simulation-only research until a separate engineering validation process supports anything further.

Useful ML examples are parameter identification, disturbance forecasting, anomaly detection, gain scheduling and uncertainty-aware tuning. Training on outputs from the same simulator and testing on nearly identical outputs proves plumbing, not real-world validity. Identification also needs informative excitation and identifiability; a single closed-loop step trace is not automatically enough to estimate every unknown.

## Agentic protocol architecture

```text
Astra: define task, assumptions, allowed changes and measurable gates
  → retrieve approved controls/math references and exact Modelica interfaces
  → MCP / OMPython: build and run bounded simulation experiments
  → Python: calculate metrics; optionally fit a statistical/ML model
  → verifier: check units, source identity, effective parameters and held-out results
  → accept, reject or choose the next experiment; retain artifacts
```

MCP is a tool interface, **not a learning algorithm, safety proof or real-time control bus**. Separate training/inference code is needed for an actual learned model. A future custom ML tool should have bounded inputs, workspace paths, budgets, seeds and structured results rather than arbitrary shell exposure.

The PI/controller/simulation solver executes the fast loop. The language-model agent operates the slower design/experiment loop. Do not route each motor torque update through an LLM/network tool call. FMI is the distinct interface family for exchanging/coupling simulation models; MCP can orchestrate those tools without replacing FMI or the numerical solver.

Reusable agent-engineering ideas also exist in `/home/nathan/quant/reference/meta/loop-engineering.md`: persistent experiment state, bounded automation and maker/checker separation. It is practitioner guidance with historical stack descriptions, not proof of an autonomous or safe system. Verifiers should compute observable gates; neither a maker nor reviewer saying “looks good” is sufficient.

## Recommended next research exercise

1. Keep the current verified PI as the baseline.
2. Define uncertainty/noise/load scenarios and reserve unseen scenarios in advance.
3. Generate public synthetic experiments with sufficiently informative applied inputs.
4. Estimate J/d or states with a simple regression/Kalman approach; validate uncertainty and residuals.
5. Tune gains across scenarios, optionally using a learned surrogate to choose experiments.
6. Compare tracking error, overshoot, settling, torque/control activity and worst-case/quantile failures on the reserved scenarios.

Split whole trajectories/scenarios; overlapping windows and correlated simulator samples must not leak between fitting and evaluation. Count the candidate search and keep the final holdout untouched. Do not transplant financial Sharpe, Pardo profit-percentage rules, Kelly sizing or Avellaneda–Stoikov quoting formulas as engineering acceptance criteria.

Keep both corpora separate. If this direction is approved for implementation, create a small reviewed controls/ML bridge collection with explicit units, assumptions, source locators and tests; do not add all trading-oriented notes to the OpenModelica forced-retrieval set.
