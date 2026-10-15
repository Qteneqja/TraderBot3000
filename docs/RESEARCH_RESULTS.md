# Provider-model selection results: October 15, 2026 UTC

All four scheduled trend comparisons completed. These are actual provider-data validation results, not simulated live trading. The sixteen artifacts remain EXPERIMENTAL. None passes validation: every base and doubled-cost replay generated zero trades at the unchanged 80% target threshold. Final tests remain NOT_EVALUATED. No model, final reservation, formal paper trial or practice order was activated.

Lower Brier is better; improving it alone does not demonstrate an executable edge. Costs and original chronological/purged/walk-forward methodology are documented in [controlled learning](CONTROLLED_LEARNING.md). The crypto fee is the explicitly assumed 1.2% per side, not a verified account rate.

| Asset | Logistic Brier | Random Forest Brier | LightGBM Brier | XGBoost Brier | Class-frequency baseline |
| --- | ---: | ---: | ---: | ---: | ---: |
| EUR_USD | 0.594236 | 0.584377 | 0.585046 | 0.582895 | 0.588009 |
| GBP_USD | 0.558769 | 0.554434 | 0.578361 | 0.589975 | 0.555170 |
| BTC-USD | 0.575372 | 0.571255 | 0.575037 | 0.576975 | 0.581252 |
| ETH-USD | 0.580119 | 0.577620 | 0.584992 | 0.589423 | 0.586535 |

## Immutable experiment identifiers

| Asset | Family | Version | Calibration / validation candidates | Evaluated walk-forward folds |
| --- | --- | --- | ---: | ---: |
| EUR_USD | logistic | candidate-logistic-433db1a0c9872b20 | 339 / 347 | 3 |
| EUR_USD | random_forest | candidate-random_forest-9c52971fd4713af6 | 339 / 347 | 3 |
| EUR_USD | lightgbm | candidate-lightgbm-07f69afee3871c81 | 339 / 347 | 3 |
| EUR_USD | xgboost | candidate-xgboost-e165d1e001ce2320 | 339 / 347 | 3 |
| GBP_USD | logistic | candidate-logistic-93ba956519629f2c | 494 / 488 | 3 |
| GBP_USD | random_forest | candidate-random_forest-3621e97405f548ff | 494 / 488 | 3 |
| GBP_USD | lightgbm | candidate-lightgbm-112725123ae0ea62 | 494 / 488 | 3 |
| GBP_USD | xgboost | candidate-xgboost-e627ce9cbf91cdaf | 494 / 488 | 3 |
| BTC-USD | logistic | candidate-logistic-b7e2a8db0c3b7a43 | 5181 / 5183 | 3 |
| BTC-USD | random_forest | candidate-random_forest-7ae691ec93cad275 | 5181 / 5183 | 3 |
| BTC-USD | lightgbm | candidate-lightgbm-8fd96bb42817fa02 | 5181 / 5183 | 3 |
| BTC-USD | xgboost | candidate-xgboost-f60172fc511e0189 | 5181 / 5183 | 3 |
| ETH-USD | logistic | candidate-logistic-bfcfd3e85137cbea | 5718 / 5719 | 3 |
| ETH-USD | random_forest | candidate-random_forest-480ed55a6405613c | 5718 / 5719 | 3 |
| ETH-USD | lightgbm | candidate-lightgbm-09f03b9c95d979c5 | 5718 / 5719 | 3 |
| ETH-USD | xgboost | candidate-xgboost-fd051facbe3cb793 | 5718 / 5719 | 3 |

## Exact failed validation gates

| Asset | Family | Failed gates |
| --- | --- | --- |
| EUR_USD | logistic | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| EUR_USD | random_forest | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| EUR_USD | lightgbm | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| EUR_USD | xgboost | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| GBP_USD | logistic | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| GBP_USD | random_forest | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| GBP_USD | lightgbm | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| GBP_USD | xgboost | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| BTC-USD | logistic | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| BTC-USD | random_forest | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| BTC-USD | lightgbm | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| BTC-USD | xgboost | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| ETH-USD | logistic | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| ETH-USD | random_forest | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| ETH-USD | lightgbm | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |
| ETH-USD | xgboost | TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN |

The immutable detailed JSON is in the ignored research volume/local data/reports/validation-selection-summary-20261015.json. Original job evidence, costs, periods, dataset manifests, calibration and stressed portfolios remain in the database/research volumes. Preserve rejected/zero-trade evidence; do not lower thresholds or reuse inspected historical final periods. Legitimate further strategy/feature/hyperparameter and regime research must remain validation-only until a frozen candidate earns a new untouched prospective test.
