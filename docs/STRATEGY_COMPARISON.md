# Bounded strategy comparisons

Measured 2026-10-15 UTC. All twenty preregistered cases are reported. No new production model was fitted or qualified.

Trend immediate entries were measured at 6/12/24/48 five-minute bars; trend pullback plus completed-hour trend confirmation at 12/48; breakout immediate and prior-bar breakout/retest confirmation at 12/48, each on EUR/USD and GBP/USD. Filters use completed current/prior bars and only hours containing twelve observed five-minute bars, joined at hour completion. They filter existing market proposals; they do not simulate limit-order execution. Different horizons receive separate diagnostic outcome schema identifiers.

| Symbol | Strategy | Entry filter | Bars | Candidates | Target % | Mean net R | Exploratory 95% mean-R interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EUR_USD | trend | IMMEDIATE | 6 | 1721 | 2.15 | -0.2154 | -0.3010, -0.1479 |
| EUR_USD | trend | IMMEDIATE | 12 | 1713 | 6.48 | -0.2326 | -0.3383, -0.1436 |
| EUR_USD | trend | IMMEDIATE | 24 | 1710 | 13.22 | -0.2160 | -0.3583, -0.0961 |
| EUR_USD | trend | IMMEDIATE | 48 | 1677 | 18.84 | -0.1692 | -0.3351, -0.0286 |
| EUR_USD | trend | PULLBACK_HTF | 12 | 46 | 17.39 | 0.3093 | -0.2282, 0.7589 |
| EUR_USD | trend | PULLBACK_HTF | 48 | 44 | 22.73 | 0.1791 | -0.4237, 0.7096 |
| EUR_USD | breakout | IMMEDIATE | 12 | 503 | 7.75 | -0.3278 | -0.4714, -0.1891 |
| EUR_USD | breakout | IMMEDIATE | 48 | 494 | 18.22 | -0.2856 | -0.4600, -0.1293 |
| EUR_USD | breakout | BREAKOUT_RETEST | 12 | 53 | 7.55 | -0.3962 | -0.6912, -0.1147 |
| EUR_USD | breakout | BREAKOUT_RETEST | 48 | 51 | 17.65 | -0.2405 | -0.6167, 0.1130 |
| GBP_USD | trend | IMMEDIATE | 6 | 2653 | 2.07 | -0.2748 | -0.3402, -0.2076 |
| GBP_USD | trend | IMMEDIATE | 12 | 2652 | 6.26 | -0.3088 | -0.4050, -0.2065 |
| GBP_USD | trend | IMMEDIATE | 24 | 2648 | 11.63 | -0.3238 | -0.4475, -0.1924 |
| GBP_USD | trend | IMMEDIATE | 48 | 2614 | 15.53 | -0.3177 | -0.4622, -0.1708 |
| GBP_USD | trend | PULLBACK_HTF | 12 | 66 | 4.55 | -0.2738 | -0.4963, -0.0645 |
| GBP_USD | trend | PULLBACK_HTF | 48 | 64 | 10.94 | -0.3559 | -0.6712, -0.0644 |
| GBP_USD | breakout | IMMEDIATE | 12 | 763 | 9.83 | -0.2481 | -0.3760, -0.1188 |
| GBP_USD | breakout | IMMEDIATE | 48 | 751 | 18.38 | -0.2900 | -0.4353, -0.1394 |
| GBP_USD | breakout | BREAKOUT_RETEST | 12 | 95 | 8.42 | -0.3038 | -0.5536, 0.0223 |
| GBP_USD | breakout | BREAKOUT_RETEST | 48 | 92 | 16.30 | -0.2968 | -0.5831, 0.0640 |


All immediate-entry trend/breakout means remain negative. EUR pullback has positive sample means but only 46/44 candidates, and both intervals cross zero. GBP pullback and both breakout-retest hypotheses have negative means. No comparison supplies robust positive evidence or sufficient calibrated trade activity.

Holding windows overlap. Intervals use 2,000 circular five-calendar-day block resamples with seed 42; they are exploratory, not multiplicity-adjusted discoveries or portfolio return bounds. The JSON also reports common-candidate paired horizon subsets (1,677 EUR and 2,614 GBP trend candidates) so changing gap/end exclusions is visible. This is a candidate-return comparison, not portfolio profit factor, drawdown, walk-forward qualification or a final test. Historical commission, financing, fills and CAD conversions remain unverified; the old estimated costs were frozen for comparability.

Next defensible step: obtain cost evidence and a separately preregistered hypothesis with enough candidates. Do not select the sparse positive EUR subset, retune on its observed outcomes, or call a longer horizon an improved deployed model.
