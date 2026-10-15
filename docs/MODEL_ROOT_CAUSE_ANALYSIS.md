# Measured model root-cause analysis

Measured 2026-10-15 UTC. Diagnostic only; no execution authority. Original final-test outcomes remain sealed.

## Data and label definitions

The original twelve-bar label is stop=0, target=1, timeout=2. It asks whether a target at least 2.5R away is reached within one hour after a valid next-bar entry. It is not the probability of any profitable exit. The stop is at least 1.5 ATR or ten instrument ticks. Target rounding preserves reward outward. Same-bar stop/target ambiguity uses stop first. Entry drift is conditioned on the modeled next-open quote. Warm-up/context and the entire outcome window must be contiguous. No gaps are filled.

The current research code contract is `43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f`. The forensic scanner exactly matches the original training features and labels under the same modeled costs in regression tests. Runtime feature parity is tested at the same quote/time. This does not prove parity with future broker fills, variable intrabar spreads or a different order type.

| Symbol | Prefix candles | Final seal (UTC) |
| --- | --- | --- |
| BTC-USD | 79111 | 2026-07-17T05:05:00+00:00 |
| ETH-USD | 80125 | 2026-07-20T17:35:00+00:00 |
| EUR_USD | 47682 | 2026-06-05T13:40:00+00:00 |
| GBP_USD | 48842 | 2026-06-11T15:00:00+00:00 |

## Outcomes before model selection

Counts include overlapping proposals, not independent trades or a risk-approved portfolio. Drift rejections are reported separately; gap counts are windows, not candidate counts. Per-direction, regime, declared DST-aware London/New York session and fixed ATR-volatility segments, holding durations, full exit-bar MFE/MAE envelopes and exploratory block intervals are in the immutable JSON.

| Symbol | Strategy | Generated | Drift rejected | Valid | Stop | Timeout | Target | Target % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BTC-USD | trend | 29968 | 2341 | 27627 | 13595 | 10904 | 3128 | 11.32 |
| BTC-USD | momentum | 21079 | 1749 | 19330 | 9838 | 7076 | 2416 | 12.50 |
| BTC-USD | mean_reversion | 3591 | 749 | 2842 | 1521 | 1018 | 303 | 10.66 |
| BTC-USD | breakout | 6645 | 895 | 5750 | 3214 | 1763 | 773 | 13.44 |
| BTC-USD | structure | 9999 | 782 | 9217 | 4818 | 3259 | 1140 | 12.37 |
| BTC-USD | volatility | 3949 | 324 | 3625 | 1945 | 1182 | 498 | 13.74 |
| ETH-USD | trend | 32929 | 2430 | 30499 | 14531 | 12398 | 3570 | 11.71 |
| ETH-USD | momentum | 22767 | 1709 | 21058 | 10300 | 8033 | 2725 | 12.94 |
| ETH-USD | mean_reversion | 3440 | 635 | 2805 | 1445 | 1079 | 281 | 10.02 |
| ETH-USD | breakout | 5926 | 674 | 5252 | 2887 | 1585 | 780 | 14.85 |
| ETH-USD | structure | 9877 | 658 | 9219 | 4679 | 3315 | 1225 | 13.29 |
| ETH-USD | volatility | 4195 | 298 | 3897 | 2015 | 1304 | 578 | 14.83 |
| EUR_USD | trend | 3505 | 1792 | 1713 | 819 | 783 | 111 | 6.48 |
| EUR_USD | momentum | 3016 | 1639 | 1377 | 676 | 607 | 94 | 6.83 |
| EUR_USD | mean_reversion | 2012 | 1785 | 227 | 110 | 97 | 20 | 8.81 |
| EUR_USD | breakout | 2736 | 2233 | 503 | 291 | 173 | 39 | 7.75 |
| EUR_USD | structure | 1477 | 847 | 630 | 367 | 221 | 42 | 6.67 |
| EUR_USD | volatility | 474 | 243 | 231 | 119 | 88 | 24 | 10.39 |
| GBP_USD | trend | 5214 | 2562 | 2652 | 1412 | 1074 | 166 | 6.26 |
| GBP_USD | momentum | 4402 | 2268 | 2134 | 1159 | 830 | 145 | 6.79 |
| GBP_USD | mean_reversion | 2162 | 1804 | 358 | 177 | 158 | 23 | 6.42 |
| GBP_USD | breakout | 3033 | 2270 | 763 | 417 | 271 | 75 | 9.83 |
| GBP_USD | structure | 2160 | 1098 | 1062 | 562 | 423 | 77 | 7.25 |
| GBP_USD | volatility | 668 | 331 | 337 | 195 | 119 | 23 | 6.82 |

## Raw versus calibrated probabilities

The comparison uses identical validation rows for each raw/calibrated pair. A common per-symbol final seal can truncate the original validation period; full stored validation metrics remain separate. All 19 calibrated models improve both Brier and log loss versus their raw estimators on these matched rows. Some still lose to the training-frequency baseline. This supports retaining calibration; it does not establish reliable high-probability opportunities. All calibrated maxima remain below .80. The catalog preserves metadata for all 57 registered versions; incompatible historical/fixture artifacts are not rescored as current models.

| Model | Matched n | Raw max | Cal max | Raw Brier | Cal Brier | Baseline Brier |
| --- | --- | --- | --- | --- | --- | --- |
| candidate-logistic-e2979ef54ebcefd8 | 5174 | 0.2379 | 0.1680 | 0.5781 | 0.5756 | 0.5817 |
| candidate-logistic-5954ee88a29ad126 | 5709 | 0.2582 | 0.1833 | 0.5902 | 0.5802 | 0.5863 |
| candidate-lightgbm-305a2e2ab41fe20e | 5709 | 0.6962 | 0.2876 | 0.5885 | 0.5832 | 0.5863 |
| candidate-xgboost-c7b647e72579515b | 5709 | 0.8689 | 0.3142 | 0.5996 | 0.5827 | 0.5863 |
| candidate-logistic-02f7a3c7e9e27847 | 191 | 0.2547 | 0.0792 | 0.5708 | 0.5516 | 0.5476 |
| candidate-lightgbm-4a57204a0971c0d4 | 191 | 0.4950 | 0.0999 | 0.6590 | 0.5552 | 0.5476 |
| candidate-xgboost-36b7bd3a48c84243 | 191 | 0.8375 | 0.1318 | 0.7497 | 0.5634 | 0.5476 |
| candidate-logistic-96a8e7e3cf4263ab | 147 | 0.2097 | 0.0797 | 0.5643 | 0.5479 | 0.5497 |
| candidate-lightgbm-46b5359d7474a570 | 147 | 0.6918 | 0.1045 | 0.6795 | 0.5563 | 0.5497 |
| candidate-xgboost-df5b1dd497ad0a85 | 147 | 0.8883 | 0.0779 | 0.7138 | 0.5534 | 0.5497 |
| candidate-logistic-3ab5431a88a4af92 | 93 | 0.5321 | 0.1009 | 0.5932 | 0.5628 | 0.5653 |
| candidate-lightgbm-f7ce4adff7f91410 | 93 | 0.8208 | 0.1677 | 0.6863 | 0.5508 | 0.5653 |
| candidate-xgboost-5badd4cd403971d3 | 93 | 0.9440 | 0.0870 | 0.7679 | 0.5574 | 0.5653 |
| candidate-logistic-fc014e90f0f1cd9d | 53 | 0.2723 | 0.0402 | 0.5258 | 0.5014 | 0.4989 |
| candidate-lightgbm-681ea00a2719fd8b | 53 | 0.7177 | 0.0594 | 0.6266 | 0.5117 | 0.4989 |
| candidate-xgboost-6990f8c28254f507 | 53 | 0.7284 | 0.0447 | 0.7234 | 0.5028 | 0.4989 |
| candidate-logistic-8ccbf2050e3870da | 498 | 0.3946 | 0.0788 | 0.5629 | 0.5568 | 0.5628 |
| candidate-lightgbm-a9108e276d677621 | 498 | 0.5525 | 0.1771 | 0.6529 | 0.5764 | 0.5628 |
| candidate-xgboost-66285615c05fbc4d | 498 | 0.8274 | 0.1900 | 0.7063 | 0.5883 | 0.5628 |

Six raw-probability sklearn log-loss normalization warnings were emitted in the forensic run; values were not silently adjusted. The horizon-filter test/run also emits a NumPy generic-timedelta deprecation warning. Neither warning is a repaired production defect. No evidence here supports removing calibration or lowering the .80 threshold.

## Separate expected-value diagnostic

Training-only mean net R for stop, target and timeout outcomes is weighted by calibrated three-class probabilities. This accounts for empirical timeout returns in research only. Eighteen models select no positive-EV validation candidates. GBP XGBoost selects three, whose observed average is -0.3604R. That result has insufficient sample size and no execution authority. The deterministic risk policy remains unchanged.

## BTC native fault

The original corrected campaign child exited -11 after registering the BTC logistic model, without a completed batch result. The old failed run remains failed. Its historical stack is unavailable. The new bounded reproduction separately completed verified logistic loading, base and doubled-cost validation replay (zero trades each), then two single-thread LightGBM fit/calibration/serialization cycles. Reloaded predictions matched exactly. Observed maximum RSS was 819620 KiB; feature memory was 3315240 bytes. The declared cap was 4 GiB address space and 900 CPU seconds; all reported native pools had one thread. Status: **NOT_REPRODUCED_UNDER_DECLARED_SINGLE_THREAD_LIMITS**. Original cause: **UNRESOLVED**. This does not prove that thread count caused the original fault or repair historical evidence.

## Decision

The target event is rare, entry drift removes many proposals, calibration reduces unsupported confidence, and the bounded alternatives do not show robust positive candidate returns. No new production model fits are justified by these results. Deep learning is deferred until a causal hypothesis has enough independent evidence and a fair bounded baseline comparison. See [strategy comparisons](STRATEGY_COMPARISON.md), [cost evidence](EXECUTION_COST_VALIDATION.md) and [experiment registry](RESEARCH_EXPERIMENT_REGISTRY.md).
