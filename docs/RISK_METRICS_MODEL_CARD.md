# SignalForge Local Risk Metrics — Model Card

**Status:** Local research diagnostic. **Version introduced:** unreleased development build following SignalForge Studio v1.1.2.

## Intended purpose

`signalforge_finance.risk_metrics` estimates univariate tail-loss statistics from a local, user-supplied sequence of historical **decimal returns**. Its intended use is inspection, comparison of stated distribution assumptions and reproducible scenario research. It is designed to work in memory and has no market-data, network, filesystem, broker or trade-execution interface.

> This component is **not** a regulatory-capital model, a Basel/FRTB internal model, a stress-testing programme, a price or return forecast, personalized investment advice, a suitability determination or an order-generation system. Regulatory Expected Shortfall sits within broader risk-factor, calibration, model-approval and backtesting requirements that are outside this component.[1]

## Inputs and units

| Input | Requirement | Interpretation |
|---|---|---|
| `returns` | One-dimensional, finite numerical sequence | Decimal return per chosen observation interval; `0.01` is +1%, `-0.01` is -1% |
| `confidence_level` | Strictly between `0.50` and `1.00` | Tail confidence used in VaR/ES calculations |
| `min_observations` | Integer at least `30` | Minimum local observations before computation |
| `simulation_count` | Integer from `1,000` to `1,000,000` | Number of normal Monte Carlo scenarios |
| `random_seed` | Integer | Seeds the local pseudo-random generator for reproducible Monte Carlo scenarios |

The loss convention is **`loss = -return`**. All reported VaR and ES values are therefore in the same decimal unit as the input returns. The implementation models exactly one supplied observation interval; it does **not** annualize, compound or apply square-root-of-time scaling.

## Methods

| Method identifier | Definition | Assumptions / disclosures |
|---|---|---|
| `historical` | Let `L = -r`. VaR is `numpy.quantile(L, c, method="higher")`; ES is the arithmetic mean of observed losses where `L >= VaR`. | Window length and deterministic observed-loss quantile rule are part of the result. Historic sampling can omit future or unprecedented tail events. |
| `normal_parametric` | With `μL = -mean(r)`, sample standard deviation `s`, and `z = Φ⁻¹(c)`, VaR is `μL + s z`; ES is `μL + s φ(z)/(1-c)`. | Assumes normally distributed returns/losses. Requires non-zero sample variation. |
| `normal_monte_carlo` | Samples `simulation_count` returns from `N(mean(r), sample_std(r))` with NumPy’s seeded `default_rng`, transforms samples to loss, then applies the historical tail rule. | A seeded sensitivity scenario, not a forecast. Retains the normality assumption and depends on pseudo-random sampling. |

## Outputs

Every `RiskEstimate` includes the method, confidence level, VaR, Expected Shortfall, source-observation count, source return mean/std, quantile method, scenario count/seed where relevant, and warning messages. Under a conventional loss tail with non-empty severe losses, ES is expected to be at least VaR. A negative risk value is not silently clamped: it can arise mathematically from a historical series that is strongly positive relative to the selected tail, and should be examined in context.

## Built-in input controls and warnings

The module blocks non-finite values, multi-dimensional inputs, samples below the configured minimum, invalid confidence values, invalid scenario counts and zero-dispersion input for normal/Monte Carlo methods. It also carries warning strings when the source sample has fewer than 250 observations, when fewer than 10 observed points fall in the historical loss tail, and whenever a normality assumption has been selected.

Warnings are part of the result rather than an error because a research user may deliberately compare small samples or parametric assumptions. A future UI or exporter must display them prominently and include them in the saved run record.

## Known limitations and non-goals

The component is univariate. It does not model cross-asset correlation, portfolios, time-varying parameters, liquidity horizons, transaction costs, nonlinear derivatives, jumps, skew, heavy tails, serial dependence, data quality, corporate actions, timezone alignment or stress-period selection. Normal methods can materially understate or mischaracterize non-normal tails. Historical estimates are sensitive to the exact sample and quantile convention. Seeded Monte Carlo reproducibility means repeated code runs share a sample; it does not make that sample a prediction.

The component is deliberately not connected to raw-data telemetry, cloud custody, external data vendors, customer accounts, brokers or exchanges. The customer retains responsibility for dataset rights, local endpoint security, review of outputs, retention and decision governance.

## Reproducibility record

Before an output is used in a report, the calling application should persist a local `RunManifest` containing the following values. A `RiskEstimate` alone is not sufficient evidence of provenance.

| Manifest field | Why it matters |
|---|---|
| Dataset label, local source identifier and cryptographic content hash | Links the result to the exact immutable local input without transmitting raw data |
| Timestamp range, observation frequency and preprocessing log | Makes the return interval, missing-data treatment and transformations reviewable |
| Return definition and unit declaration | Prevents price/percent/decimal or close-to-close ambiguity |
| `RiskConfig`, method, confidence and quantile method | Reconstructs the calculation choice |
| Random seed and scenario count | Recreates Monte Carlo output |
| SignalForge package version; NumPy/SciPy versions; operating environment | Supports numerical reproducibility across releases |
| Output values, warnings and output hash | Preserves the result and its material caveats |
| Analyst review/approval metadata, if applicable | Separates technical output from human decision accountability |

## Verification evidence

The initial unit test set covers a hand-computable historical VaR/ES fixture, the expected ES-versus-VaR tail relation, same-seed Monte Carlo equality, changed-seed scenario variation with stable source statistics, invalid input rejection and zero-dispersion guards. This is software verification for stated behavior, not validation that any method predicts future losses or satisfies a regulatory model standard.

## References

[1]: [Bank for International Settlements — MAR33: Internal models approach: capital requirements calculation](https://www.bis.org/basel_framework/chapter/MAR/33.htm?inforce=20220101&published=20191215)
