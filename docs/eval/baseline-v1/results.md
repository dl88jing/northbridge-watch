# Evaluation results

Generated 2026-10-25 07:57 UTC on `Linux x86_64, 8 CPUs`, OpenCV 5.0.0, Python 3.13.5, n=40 per family per condition, split=test (seed0=50000).

## Canonical demo fixtures (5 images)

| Scene | Expected | Predicted | Conf | #det | Action | p50 ms |
|---|---|---|---|---|---|---|
| calm_porch | none | none | 0.00 | 0 | noop | 1.56 |
| package_at_door | package | package | 0.82 | 1 | notify | 1.83 |
| floor_spill | spill | spill | 0.68 | 1 | human_required | 2.82 |
| empty_fridge | empty_fridge | empty_fridge | 0.76 | 1 | notify | 1.45 |
| busy_porch | package | package | 0.66 | 3 | human_required | 1.60 |

## In-domain randomized scenes (7 families)

| Condition | N | Label acc | Action acc | Package P/R | Spill P/R | Empty-fridge P/R | Busy count exact | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| clean | 280 | 0.829 | 0.825 | 1.000 / 0.975 | 1.000 / 0.850 | 0.500 / 1.000 | 0.925 | 2.15 | 3.19 |
| photometric | 280 | 0.807 | 0.800 | 1.000 / 0.963 | 1.000 / 0.550 | 0.549 / 0.975 | 0.850 | 2.12 | 3.37 |
| blur_noise | 280 | 0.839 | 0.839 | 1.000 / 1.000 | 1.000 / 0.875 | 0.500 / 1.000 | 1.000 | 2.00 | 2.90 |
| jpeg_q30 | 280 | 0.832 | 0.829 | 1.000 / 0.975 | 1.000 / 0.875 | 0.500 / 1.000 | 0.900 | 2.19 | 3.18 |
| half_res | 280 | 0.446 | 0.446 | n/a / 0.000 | 1.000 / 0.125 | 0.500 / 1.000 | 0.000 | 0.62 | 0.97 |

### Per-family label accuracy

| Family | clean | photometric | blur_noise | jpeg_q30 | half_res |
|---|---|---|---|---|---|
| calm_porch | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| package_at_door | 0.95 (none:2) | 0.93 (none:3) | 1.00 | 0.95 (none:2) | 0.00 (none:40) |
| busy_porch | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 (none:40) |
| floor_spill | 0.85 (none:6) | 0.55 (none:18) | 0.88 (none:5) | 0.88 (none:5) | 0.12 (none:35) |
| clean_floor | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| empty_fridge | 1.00 | 0.97 (none:1) | 1.00 | 1.00 | 1.00 |
| full_fridge | 0.00 (empty_fridge:40) | 0.20 (empty_fridge:32) | 0.00 (empty_fridge:40) | 0.00 (empty_fridge:40) | 0.00 (empty_fridge:40) |

## Out-of-domain families (clean condition)

| Condition | N | Label acc | Action acc | Package P/R | Spill P/R | Empty-fridge P/R | Busy count exact | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| clean | 120 | 0.333 | 0.333 | 1.000 / 0.500 | n/a / 0.000 | n/a | n/a | 2.35 | 3.42 |

### Per-family label accuracy

| Family | clean |
|---|---|
| coffee_spill | 0.00 (none:40) |
| white_mailer | 0.00 (none:40) |
| night_porch_package | 1.00 |
