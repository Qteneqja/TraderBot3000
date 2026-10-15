# Final model qualification report

Evidence snapshot: 2026-10-15T17:45:44.808442+00:00. Campaign: `activation-corrected-20261015-v1`.

**Decision: NOT QUALIFIED. No model is eligible for activation. The genuinely future final test has NOT STARTED.**

This is an actual provider-data selection report. It is not a passing final-test certificate. Final model scores and final portfolio results remain sealed. All registered models remain EXPERIMENTAL.

Strategy/evaluation source contract: `43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f`. Predeclared contract: `43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f`. The strategy identity remains v1; exact evaluated source is bound by this hash, rather than a retroactively changed artifact.

## Completed model comparisons

Lower multiclass Brier is better. Calibration error is target reliability error, not win rate. Every completed model below produced zero base and doubled-cost validation trades at the unchanged 80% threshold.

| Asset / strategy | Family | Model version | Brier / class baseline | Calibration error | Calibration / validation samples |
| --- | --- | --- | --- | --- | --- |
| GBP_USD / trend | logistic | `candidate-logistic-8ccbf2050e3870da` | 0.556787 / 0.562811 | 0.013113 | 488 / 498 |
| GBP_USD / trend | lightgbm | `candidate-lightgbm-a9108e276d677621` | 0.576365 / 0.562811 | 0.033710 | 488 / 498 |
| GBP_USD / trend | xgboost | `candidate-xgboost-66285615c05fbc4d` | 0.588287 / 0.562811 | 0.012525 | 488 / 498 |
| EUR_USD / trend | logistic | `candidate-logistic-02f7a3c7e9e27847` | 0.588736 / 0.586934 | 0.052075 | 351 / 348 |
| EUR_USD / trend | lightgbm | `candidate-lightgbm-4a57204a0971c0d4` | 0.595694 / 0.586934 | 0.054408 | 351 / 348 |
| EUR_USD / trend | xgboost | `candidate-xgboost-36b7bd3a48c84243` | 0.599679 / 0.586934 | 0.059659 | 351 / 348 |
| EUR_USD / structure | logistic | `candidate-logistic-fc014e90f0f1cd9d` | 0.585021 / 0.608020 | 0.044180 | 132 / 131 |
| EUR_USD / structure | lightgbm | `candidate-lightgbm-681ea00a2719fd8b` | 0.650322 / 0.608020 | 0.042681 | 132 / 131 |
| EUR_USD / structure | xgboost | `candidate-xgboost-6990f8c28254f507` | 0.598953 / 0.608020 | 0.044839 | 132 / 131 |
| EUR_USD / momentum | logistic | `candidate-logistic-96a8e7e3cf4263ab` | 0.599800 / 0.596355 | 0.053920 | 275 / 282 |
| EUR_USD / momentum | lightgbm | `candidate-lightgbm-46b5359d7474a570` | 0.606261 / 0.596355 | 0.057222 | 275 / 282 |
| EUR_USD / momentum | xgboost | `candidate-xgboost-df5b1dd497ad0a85` | 0.602802 / 0.596355 | 0.058262 | 275 / 282 |
| ETH-USD / trend | logistic | `candidate-logistic-5954ee88a29ad126` | 0.580165 / 0.586293 | 0.021293 | 5711 / 5709 |
| ETH-USD / trend | lightgbm | `candidate-lightgbm-305a2e2ab41fe20e` | 0.583169 / 0.586293 | 0.019075 | 5711 / 5709 |
| ETH-USD / trend | xgboost | `candidate-xgboost-c7b647e72579515b` | 0.582728 / 0.586293 | 0.017715 | 5711 / 5709 |
| EUR_USD / breakout | logistic | `candidate-logistic-3ab5431a88a4af92` | 0.562813 / 0.565256 | 0.016657 | 93 / 93 |
| EUR_USD / breakout | lightgbm | `candidate-lightgbm-f7ce4adff7f91410` | 0.550828 / 0.565256 | 0.015328 | 93 / 93 |
| EUR_USD / breakout | xgboost | `candidate-xgboost-5badd4cd403971d3` | 0.557426 / 0.565256 | 0.006860 | 93 / 93 |

## Exact evidence and failed checks

Input intervals below are stored candle timestamps. Partition intervals are candidate decision timestamps; the trainer purges overlapping outcome windows. Test timestamps identify the sealed historical partition, which does not replace a new prospective final period.

### GBP_USD / trend: COMPLETED

Durable run: `5717cc199527a6283c3c583ddb58eb579d95e6a76b0ea311c6398580ce769684`.

Cost assumptions: spread=.00019; slippage=.00001; fee_rate=0; financing_per_bar=0.

Cost provenance/limitations: FX: median close bid/ask spread of Oct14-21 2025; 1 tick adverse slippage; zero simulation fees/financing are UNVERIFIED assumptions, not broker charges.; bounded corrected-code research campaign activation-corrected-20261015-v1; code 43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f

- `candidate-logistic-8ccbf2050e3870da`: artifact SHA256 `e2eb43af8b3bfe28cebea05b29ae32a3d87e3677b14d835554054f465373fe71`; dataset/configuration SHA256 `8ccbf2050e3870da0e99333237f18593ef3d84b4c87901e34475799e801608ed`.
  Input: `{"count": 74577, "end": "2026-10-14T23:55:00+00:00", "sha256": "bb6577c2831afe7a5e1c9babe6815fe9f441d42fc2812f49ca0d43d01a444a8a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-18 19:10:00+00:00", "2026-04-02 12:50:00+00:00"], "test": ["2026-06-11 15:00:00+00:00", "2026-10-14 16:50:00+00:00"], "train": ["2025-10-15 15:20:00+00:00", "2026-03-18 14:45:00+00:00"], "validation": ["2026-04-02 15:45:00+00:00", "2026-06-11 01:55:00+00:00"]}`.
  Coverage: 0.99979821; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[498, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-lightgbm-a9108e276d677621`: artifact SHA256 `64f1474ce373566f6c4d140eebbe14e2e1195f1433d11e9a994871e0394ff610`; dataset/configuration SHA256 `a9108e276d6776217a42b013a862820b8008284e5a422a7ba651aa86b6d65e68`.
  Input: `{"count": 74577, "end": "2026-10-14T23:55:00+00:00", "sha256": "bb6577c2831afe7a5e1c9babe6815fe9f441d42fc2812f49ca0d43d01a444a8a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-18 19:10:00+00:00", "2026-04-02 12:50:00+00:00"], "test": ["2026-06-11 15:00:00+00:00", "2026-10-14 16:50:00+00:00"], "train": ["2025-10-15 15:20:00+00:00", "2026-03-18 14:45:00+00:00"], "validation": ["2026-04-02 15:45:00+00:00", "2026-06-11 01:55:00+00:00"]}`.
  Coverage: 0.99979821; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[424, 74, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-xgboost-66285615c05fbc4d`: artifact SHA256 `bf343c978a33dda129417530aa32c831c29fbbdca26621ade467201fcee5293c`; dataset/configuration SHA256 `66285615c05fbc4d6e83fe7f7ed1fc68ef5d05ba84de3af06e76232c059886a7`.
  Input: `{"count": 74577, "end": "2026-10-14T23:55:00+00:00", "sha256": "bb6577c2831afe7a5e1c9babe6815fe9f441d42fc2812f49ca0d43d01a444a8a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-18 19:10:00+00:00", "2026-04-02 12:50:00+00:00"], "test": ["2026-06-11 15:00:00+00:00", "2026-10-14 16:50:00+00:00"], "train": ["2025-10-15 15:20:00+00:00", "2026-03-18 14:45:00+00:00"], "validation": ["2026-04-02 15:45:00+00:00", "2026-06-11 01:55:00+00:00"]}`.
  Coverage: 0.99979821; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[482, 16, 0, 0, 0, 0, 0, 0, 0, 0]`.


### EUR_USD / trend: COMPLETED

Durable run: `6a5f0f1a9363ca67b9148a44bd7242a7a8861df4dbb388ab633cb3b98f2f8fb6`.

Cost assumptions: spread=.00016; slippage=.00001; fee_rate=0; financing_per_bar=0.

Cost provenance/limitations: FX: median close bid/ask spread of Oct14-21 2025; 1 tick adverse slippage; zero simulation fees/financing are UNVERIFIED assumptions, not broker charges.; bounded corrected-code research campaign activation-corrected-20261015-v1; code 43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f

- `candidate-logistic-02f7a3c7e9e27847`: artifact SHA256 `61c797fcf25451559f5063eb154f70861f8b04ab5a0df59743b7931a802accef`; dataset/configuration SHA256 `02f7a3c7e9e27847d4681b3f216eeae6c64379c6df4f28d4beec9f3969bc1708`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-19 20:20:00+00:00", "2026-04-13 14:35:00+00:00"], "test": ["2026-06-30 15:15:00+00:00", "2026-10-14 15:50:00+00:00"], "train": ["2025-10-17 12:25:00+00:00", "2026-03-19 19:15:00+00:00"], "validation": ["2026-04-13 17:05:00+00:00", "2026-06-26 16:35:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, CALIBRATION, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[348, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-lightgbm-4a57204a0971c0d4`: artifact SHA256 `f377227e73bfcfb3890b56e77338c9a83c5caf150bf1ace0c239c961fa8c1d11`; dataset/configuration SHA256 `4a57204a0971c0d454c081306bfc10fc8f1bb62b411b2c832cbac39113b8955b`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-19 20:20:00+00:00", "2026-04-13 14:35:00+00:00"], "test": ["2026-06-30 15:15:00+00:00", "2026-10-14 15:50:00+00:00"], "train": ["2025-10-17 12:25:00+00:00", "2026-03-19 19:15:00+00:00"], "validation": ["2026-04-13 17:05:00+00:00", "2026-06-26 16:35:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, CALIBRATION, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[348, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-xgboost-36b7bd3a48c84243`: artifact SHA256 `87c963e35e4f34521c78f1689d70d556096ee5e04cb9253072b54f541903aa15`; dataset/configuration SHA256 `36b7bd3a48c84243309c148cb65b573b113091e9ce77c4b98d907ae49c8699df`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-19 20:20:00+00:00", "2026-04-13 14:35:00+00:00"], "test": ["2026-06-30 15:15:00+00:00", "2026-10-14 15:50:00+00:00"], "train": ["2025-10-17 12:25:00+00:00", "2026-03-19 19:15:00+00:00"], "validation": ["2026-04-13 17:05:00+00:00", "2026-06-26 16:35:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, CALIBRATION, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[345, 3, 0, 0, 0, 0, 0, 0, 0, 0]`.


### EUR_USD / structure: COMPLETED

Durable run: `a0048bbb91fa57e5dadf394b3b5a0cd019b61ff1f562bc8a5847a380ab7dde2f`.

Cost assumptions: spread=.00016; slippage=.00001; fee_rate=0; financing_per_bar=0.

Cost provenance/limitations: FX: median close bid/ask spread of Oct14-21 2025; 1 tick adverse slippage; zero simulation fees/financing are UNVERIFIED assumptions, not broker charges.; bounded corrected-code research campaign activation-corrected-20261015-v1; code 43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f

- `candidate-logistic-fc014e90f0f1cd9d`: artifact SHA256 `1ae45768fa61a9c07c562c9ad7fed563f42f2d051ef0467b9e083820f7e86370`; dataset/configuration SHA256 `fc014e90f0f1cd9d1d3c7c84df78227095a389560bcd4be6457dafc20a148272`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-23 09:55:00+00:00", "2026-04-17 16:05:00+00:00"], "test": ["2026-07-02 12:50:00+00:00", "2026-10-14 15:15:00+00:00"], "train": ["2025-10-17 12:25:00+00:00", "2026-03-20 14:35:00+00:00"], "validation": ["2026-04-17 17:10:00+00:00", "2026-07-01 13:25:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: CALIBRATION_SAMPLE_COUNT, WALK_FORWARD_VERIFIED.
  Walk-forward states: INSUFFICIENT, INSUFFICIENT, INSUFFICIENT.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[131, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-lightgbm-681ea00a2719fd8b`: artifact SHA256 `09d118784457b06f75a9cff78d1c7aaa41bc874abae6867446146848f204612b`; dataset/configuration SHA256 `681ea00a2719fd8bd2ae80754b009089374669f4e41d3cfc9867e0a4bb162fe5`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-23 09:55:00+00:00", "2026-04-17 16:05:00+00:00"], "test": ["2026-07-02 12:50:00+00:00", "2026-10-14 15:15:00+00:00"], "train": ["2025-10-17 12:25:00+00:00", "2026-03-20 14:35:00+00:00"], "validation": ["2026-04-17 17:10:00+00:00", "2026-07-01 13:25:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: CALIBRATION_SAMPLE_COUNT, WALK_FORWARD_VERIFIED.
  Walk-forward states: INSUFFICIENT, INSUFFICIENT, INSUFFICIENT.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[131, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-xgboost-6990f8c28254f507`: artifact SHA256 `1b14d4deadf4e6f28ab9e3acfcc7a7fda2f5090da856008db0d03e85afef74d7`; dataset/configuration SHA256 `6990f8c28254f507c853b16bfaef729a13f3c5ebf32549e3ebc5768deefce4f0`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-23 09:55:00+00:00", "2026-04-17 16:05:00+00:00"], "test": ["2026-07-02 12:50:00+00:00", "2026-10-14 15:15:00+00:00"], "train": ["2025-10-17 12:25:00+00:00", "2026-03-20 14:35:00+00:00"], "validation": ["2026-04-17 17:10:00+00:00", "2026-07-01 13:25:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: CALIBRATION_SAMPLE_COUNT, WALK_FORWARD_VERIFIED.
  Walk-forward states: INSUFFICIENT, INSUFFICIENT, INSUFFICIENT.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[131, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.


### EUR_USD / volatility: FAILED

Durable run: `ac9444becdc66f16d360c5ae21e0f1bff4eaacbc68c90ccac37f6215dbe44483`.

Cost assumptions: spread=.00016; slippage=.00001; fee_rate=0; financing_per_bar=0.

Cost provenance/limitations: FX: median close bid/ask spread of Oct14-21 2025; 1 tick adverse slippage; zero simulation fees/financing are UNVERIFIED assumptions, not broker charges.; bounded corrected-code research campaign activation-corrected-20261015-v1; code 43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f

- logistic: FAILED — Only 282 filled candidates; need at least 300 before purging.
- lightgbm: FAILED — Only 282 filled candidates; need at least 300 before purging.
- xgboost: FAILED — Only 282 filled candidates; need at least 300 before purging.

### EUR_USD / momentum: COMPLETED

Durable run: `b2b550aec8d7d220de9d6ece17183e66c43348eeeec46823f20a322cb85c7a47`.

Cost assumptions: spread=.00016; slippage=.00001; fee_rate=0; financing_per_bar=0.

Cost provenance/limitations: FX: median close bid/ask spread of Oct14-21 2025; 1 tick adverse slippage; zero simulation fees/financing are UNVERIFIED assumptions, not broker charges.; bounded corrected-code research campaign activation-corrected-20261015-v1; code 43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f

- `candidate-logistic-96a8e7e3cf4263ab`: artifact SHA256 `5787110ec8f3586215246e7f5aa3ea07d53183c05208b4b1cfb575a7046acc59`; dataset/configuration SHA256 `96a8e7e3cf4263ab6a2231dfaa239bdac21a58c516b3cbdf93e4c150b4ff24a6`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-20 14:55:00+00:00", "2026-04-14 07:50:00+00:00"], "test": ["2026-06-30 15:10:00+00:00", "2026-10-14 15:45:00+00:00"], "train": ["2025-10-17 12:25:00+00:00", "2026-03-20 10:20:00+00:00"], "validation": ["2026-04-17 13:45:00+00:00", "2026-06-26 16:35:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, CALIBRATION, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[282, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-lightgbm-46b5359d7474a570`: artifact SHA256 `9ee779bea58323c7b83f390a005337a2548ef2ec628c26ddf6927709942890d8`; dataset/configuration SHA256 `46b5359d7474a57067742d6ec494c99d713e53cb41ce4a1c5263b23e706d62d4`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-20 14:55:00+00:00", "2026-04-14 07:50:00+00:00"], "test": ["2026-06-30 15:10:00+00:00", "2026-10-14 15:45:00+00:00"], "train": ["2025-10-17 12:25:00+00:00", "2026-03-20 10:20:00+00:00"], "validation": ["2026-04-17 13:45:00+00:00", "2026-06-26 16:35:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, CALIBRATION, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[281, 1, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-xgboost-df5b1dd497ad0a85`: artifact SHA256 `ccb5e624e820c4a6e52e069ded53094f268434daff957aa0a6dca604b8bdb75e`; dataset/configuration SHA256 `df5b1dd497ad0a855adcac79136fb2d9fa5e368a2b00d7cf904dc9ff2c5c82b0`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-20 14:55:00+00:00", "2026-04-14 07:50:00+00:00"], "test": ["2026-06-30 15:10:00+00:00", "2026-10-14 15:45:00+00:00"], "train": ["2025-10-17 12:25:00+00:00", "2026-03-20 10:20:00+00:00"], "validation": ["2026-04-17 13:45:00+00:00", "2026-06-26 16:35:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, CALIBRATION, BEATS_CLASS_BASELINE, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[282, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.


### EUR_USD / mean_reversion: FAILED

Durable run: `bf455a49bcf3dfd81e5671e42ea33aea27b2daa3f17b80086e984f3290da8b12`.

Cost assumptions: spread=.00016; slippage=.00001; fee_rate=0; financing_per_bar=0.

Cost provenance/limitations: FX: median close bid/ask spread of Oct14-21 2025; 1 tick adverse slippage; zero simulation fees/financing are UNVERIFIED assumptions, not broker charges.; bounded corrected-code research campaign activation-corrected-20261015-v1; code 43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f

- logistic: FAILED — Only 261 filled candidates; need at least 300 before purging.
- lightgbm: FAILED — Only 261 filled candidates; need at least 300 before purging.
- xgboost: FAILED — Only 261 filled candidates; need at least 300 before purging.

### ETH-USD / trend: COMPLETED

Durable run: `c5a43e0129224ec7794518cbb6fc7e8836145bbc199c182a760cd563ee7f231f`.

Cost assumptions: spread=0.79; slippage=.01; fee_rate=.012; financing_per_bar=0.

Cost provenance/limitations: Crypto: assumed 2bps full spread from first-week median close, 1 tick slippage, 1.2 percent taker fee per side. Conservative research assumptions, not verified account charges. No maker discount or fee-free execution. Zero financing is unverified. No crypto execution authority.; bounded corrected-code research campaign activation-corrected-20261015-v1; code 43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f

- `candidate-logistic-5954ee88a29ad126`: artifact SHA256 `8e0159e28f83bf64ea3e69c1c20573ee25e0617ac96bbd37c35e4c4267697821`; dataset/configuration SHA256 `5954ee88a29ad126953c934819cd079501511d00c9f2afeca0a56f498c0ae14c`.
  Input: `{"count": 104971, "end": "2026-10-14T23:55:00+00:00", "sha256": "16a3a5e563c09efe6e57c5e2f5aa4b3c63031afe9e6492ffe077b584a6d1452b", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-30 05:30:00+00:00", "2026-05-25 21:40:00+00:00"], "test": ["2026-07-20 17:35:00+00:00", "2026-10-14 23:00:00+00:00"], "train": ["2025-10-15 05:00:00+00:00", "2026-03-30 04:25:00+00:00"], "validation": ["2026-05-25 22:45:00+00:00", "2026-07-20 16:30:00+00:00"]}`.
  Coverage: 0.99858257; usable days: 365. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[394, 5315, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-lightgbm-305a2e2ab41fe20e`: artifact SHA256 `bf076c8d6c0a11fcdcc76a340c75148076d0f76551ea1fe8ed55aff06c8d2426`; dataset/configuration SHA256 `305a2e2ab41fe20ee0fc2ce97475d97b967aad2ffde748d1d9894ae1f91bd13d`.
  Input: `{"count": 104971, "end": "2026-10-14T23:55:00+00:00", "sha256": "16a3a5e563c09efe6e57c5e2f5aa4b3c63031afe9e6492ffe077b584a6d1452b", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-30 05:30:00+00:00", "2026-05-25 21:40:00+00:00"], "test": ["2026-07-20 17:35:00+00:00", "2026-10-14 23:00:00+00:00"], "train": ["2025-10-15 05:00:00+00:00", "2026-03-30 04:25:00+00:00"], "validation": ["2026-05-25 22:45:00+00:00", "2026-07-20 16:30:00+00:00"]}`.
  Coverage: 0.99858257; usable days: 365. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[3926, 1682, 101, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-xgboost-c7b647e72579515b`: artifact SHA256 `35b7b35746a9cb15b09769571c22d4c69430dbfbb85d724a53a2229d9bc0f821`; dataset/configuration SHA256 `c7b647e72579515bb38e1a85c5533c588125db18fe1bc682877c294572e788ab`.
  Input: `{"count": 104971, "end": "2026-10-14T23:55:00+00:00", "sha256": "16a3a5e563c09efe6e57c5e2f5aa4b3c63031afe9e6492ffe077b584a6d1452b", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-30 05:30:00+00:00", "2026-05-25 21:40:00+00:00"], "test": ["2026-07-20 17:35:00+00:00", "2026-10-14 23:00:00+00:00"], "train": ["2025-10-15 05:00:00+00:00", "2026-03-30 04:25:00+00:00"], "validation": ["2026-05-25 22:45:00+00:00", "2026-07-20 16:30:00+00:00"]}`.
  Coverage: 0.99858257; usable days: 365. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: none in these two checks.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[2456, 3152, 99, 2, 0, 0, 0, 0, 0, 0]`.


### EUR_USD / breakout: COMPLETED

Durable run: `c6811ec03b4a331665d667d2bd119bd54568c88df8d2ee7b0e5159966f838457`.

Cost assumptions: spread=.00016; slippage=.00001; fee_rate=0; financing_per_bar=0.

Cost provenance/limitations: FX: median close bid/ask spread of Oct14-21 2025; 1 tick adverse slippage; zero simulation fees/financing are UNVERIFIED assumptions, not broker charges.; bounded corrected-code research campaign activation-corrected-20261015-v1; code 43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f

- `candidate-logistic-3ab5431a88a4af92`: artifact SHA256 `5598a0e07e3a90a7b44637cfb99ee293eb92acaeb25161e7cfd2e418665dfa89`; dataset/configuration SHA256 `3ab5431a88a4af92dc45884444104e1eb616ca4daa4a5542a34e4ff37f554e7c`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-17 12:10:00+00:00", "2026-03-31 13:20:00+00:00"], "test": ["2026-06-05 13:40:00+00:00", "2026-10-14 13:05:00+00:00"], "train": ["2025-10-15 13:05:00+00:00", "2026-03-16 18:30:00+00:00"], "validation": ["2026-03-31 14:35:00+00:00", "2026-06-01 21:25:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: CALIBRATION_SAMPLE_COUNT.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[92, 1, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-lightgbm-f7ce4adff7f91410`: artifact SHA256 `5b6f9c39fd097207c3be948ba6b513c21c6d8faf2318c7c82bed5b28e72b1f97`; dataset/configuration SHA256 `f7ce4adff7f91410d9cf1bb76b704141cde437af5eea5caea5bd090503d2b611`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-17 12:10:00+00:00", "2026-03-31 13:20:00+00:00"], "test": ["2026-06-05 13:40:00+00:00", "2026-10-14 13:05:00+00:00"], "train": ["2025-10-15 13:05:00+00:00", "2026-03-16 18:30:00+00:00"], "validation": ["2026-03-31 14:35:00+00:00", "2026-06-01 21:25:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: CALIBRATION_SAMPLE_COUNT.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[67, 26, 0, 0, 0, 0, 0, 0, 0, 0]`.

- `candidate-xgboost-5badd4cd403971d3`: artifact SHA256 `2defd44dc7108b232f276655f6890020644bfb7ccfd3cb394dbfae873735301a`; dataset/configuration SHA256 `5badd4cd403971d3c272479251b329bb5b44b6e2032b666128b135590108beb1`.
  Input: `{"count": 74589, "end": "2026-10-14T23:55:00+00:00", "sha256": "87ecae734d655f833087dba653bac9b5cc990cc23650fcb6f47ec4a2cbc9a85a", "start": "2025-10-15T00:00:00+00:00"}`.
  Partitions: `{"calibration": ["2026-03-17 12:10:00+00:00", "2026-03-31 13:20:00+00:00"], "test": ["2026-06-05 13:40:00+00:00", "2026-10-14 13:05:00+00:00"], "train": ["2025-10-15 13:05:00+00:00", "2026-03-16 18:30:00+00:00"], "validation": ["2026-03-31 14:35:00+00:00", "2026-06-01 21:25:00+00:00"]}`.
  Coverage: 0.99995964; usable days: 259. Current code matches: True; policy matches: True.
  Validation trades: 0; net return: 0.0; drawdown: 0.0; profit factor: None; expectancy: None. Doubled-cost trades: 0.
  Failed validation economics/calibration checks: TRADE_COUNT, ACTIVE_DAYS, POSITIVE_NET_RETURN, POSITIVE_EXPECTANCY, PROFIT_FACTOR, UNCERTAINTY_LOWER_BOUND, STRESSED_ACTIVITY, STRESSED_NET_RETURN.
  Additional recorded prerequisite failures: CALIBRATION_SAMPLE_COUNT.
  Walk-forward states: EVALUATED, EVALUATED, EVALUATED.
  Validation target-probability histogram (bins [0,.1) through [.9,1]): `[93, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.


### BTC-USD / trend: FAILED

Durable run: `ec111aab50d9a28a7a7ad98a81cb1f16e3358e00bcbd9d95f05c9564d944ff68`.

Cost assumptions: spread=21.89; slippage=.01; fee_rate=.012; financing_per_bar=0.

Cost provenance/limitations: Crypto: assumed 2bps full spread from first-week median close, 1 tick slippage, 1.2 percent taker fee per side. Conservative research assumptions, not verified account charges. No maker discount or fee-free execution. Zero financing is unverified. No crypto execution authority.; bounded corrected-code research campaign activation-corrected-20261015-v1; code 43ed4160be478938dc37ed9c2ea28d99b1a8ff15b7fa0a13b2a66e4b0b6fce0f

Batch failed: `{"exit_code": -11, "failure": "CHILD_EXITED_WITHOUT_RESULT"}`. No automatic retry or successful evaluation is inferred.


## Qualification criteria and future-test status

Policy `research-screen-v3` / SHA256 `943286b42bf10f31a592dba73c0da5faffc9750960cd6254d23af6dfd2570911` remains unchanged: 180 history/usable days, 99% session completeness, three pre-test walk-forward folds, 200 calibration samples, 30-day partitions, 100 trades and 20 active days per partition, positive net return/expectancy, profit factor at least 1.2, drawdown at most 8%, target calibration error at most .05, Brier better than the training-frequency baseline, positive block-bootstrap lower bound and positive doubled-cost activity/returns.

Zero-trade return and drawdown equal zero because there was no exposure. Profit factor, win rate, entry/exit statistics and expectancy are undefined; they are not profitable or safe performance evidence. The no-trade return baseline is zero. Some models improve Brier alone, but that does not qualify them.

The observed validation probability histograms explain abstention: none of the completed models reaches .80. Sparse mean-reversion/volatility hypotheses fail sample requirements before fitting. Changing thresholds to obtain activity would change the question, not validate these models.

No passing candidate, reservation, final-test timestamp, final-test artifact or final-test score exists. A qualifying frozen candidate would require a disjoint genuinely future observation period of at least 45 days, plus the full 12 five-minute-bar outcome horizon. That clock has not started. Future evaluation runs once without refitting, and failure consumes the attempt.

Independent executable fee/slippage/financing evidence, regime/portfolio review, explicit PAPER approval and a formal elapsed paper trial remain outstanding. OANDA practice requires the additional broker acceptance sequence. Real-money execution remains unsupported.

The failed BTC batch registered logistic artifact `candidate-logistic-e2979ef54ebcefd8` before its native child exited -11. Preserve it as incomplete evidence; no completed base/stress batch result or qualification is inferred. The native root cause is unresolved. Isolated crash tracing is added for future research children; it does not repair or retry that past process.

## Reproduction

The immutable full JSON is in the ignored research volume at `data/reports/activation-corrected-validation-completed-20261015.json`. It contains exact run IDs, plans, costs, hashes, sample counts, partitions, walk-forward metrics and failed checks. The declaration was persisted before fitting. The nine campaign schedules were disabled after all jobs were claimed to prevent unintended annual repeats; the original twelve weekly schedules are unchanged.

```powershell
docker compose exec backend python -m app.cli research-campaign-report activation-corrected-20261015-v1 --output data/reports/NEW-UNIQUE.json
.venv/Scripts/python.exe scripts/render_qualification_report.py data/reports/activation-corrected-validation-completed-20261015.json --output docs/FINAL_MODEL_QUALIFICATION_REPORT.md
```

Rendering does not evaluate markets or modify model state. New experiments must preserve the old attempts, use predeclared plans and keep final observations separate. No test or policy gate was weakened.
