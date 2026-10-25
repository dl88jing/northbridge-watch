# Evaluation results

Generated 2026-10-25 07:56 UTC on `Linux x86_64, 8 CPUs`, OpenCV 5.0.0, Python 3.13.5, n=40 per family per condition, split=test (seed0=50000).

## Canonical demo fixtures (5 images)

| Scene | Expected | Predicted | Conf | #det | Action | p50 ms |
|---|---|---|---|---|---|---|
| calm_porch | none | none | 0.00 | 0 | noop | 1.30 |
| package_at_door | package | package | 0.82 | 1 | notify | 1.38 |
| floor_spill | spill | spill | 0.68 | 1 | human_required | 2.67 |
| empty_fridge | empty_fridge | empty_fridge | 0.76 | 1 | notify | 2.03 |
| busy_porch | package | package | 0.66 | 3 | human_required | 1.63 |

## In-domain randomized scenes (7 families)

| Condition | N | Label acc | Action acc | Package P/R | Spill P/R | Empty-fridge P/R | Busy count exact | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| clean | 280 | 0.968 | 0.964 | 1.000 / 0.975 | 1.000 / 0.875 | 1.000 / 0.950 | 0.925 | 2.46 | 3.57 |
| photometric | 280 | 0.921 | 0.914 | 1.000 / 0.963 | 1.000 / 0.700 | 0.971 / 0.850 | 0.850 | 2.36 | 3.35 |
| blur_noise | 280 | 0.975 | 0.975 | 1.000 / 1.000 | 1.000 / 0.875 | 1.000 / 0.950 | 1.000 | 2.05 | 3.04 |
| jpeg_q30 | 280 | 0.968 | 0.964 | 1.000 / 0.975 | 1.000 / 0.875 | 1.000 / 0.950 | 0.900 | 2.49 | 3.65 |
| half_res | 280 | 0.968 | 0.964 | 1.000 / 0.975 | 1.000 / 0.875 | 1.000 / 0.950 | 0.925 | 2.77 | 3.90 |

### Per-family label accuracy

| Family | clean | photometric | blur_noise | jpeg_q30 | half_res |
|---|---|---|---|---|---|
| calm_porch | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| package_at_door | 0.95 (none:2) | 0.93 (none:3) | 1.00 | 0.95 (none:2) | 0.95 (none:2) |
| busy_porch | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| floor_spill | 0.88 (none:5) | 0.70 (none:12) | 0.88 (none:5) | 0.88 (none:5) | 0.88 (none:5) |
| clean_floor | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| empty_fridge | 0.95 (none:2) | 0.85 (none:6) | 0.95 (none:2) | 0.95 (none:2) | 0.95 (none:2) |
| full_fridge | 1.00 | 0.97 (empty_fridge:1) | 1.00 | 1.00 | 1.00 |

## Out-of-domain families (clean condition)

| Condition | N | Label acc | Action acc | Package P/R | Spill P/R | Empty-fridge P/R | Busy count exact | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| clean | 120 | 0.333 | 0.333 | 1.000 / 0.500 | n/a / 0.000 | n/a | n/a | 2.49 | 3.69 |

### Per-family label accuracy

| Family | clean |
|---|---|
| coffee_spill | 0.00 (none:40) |
| white_mailer | 0.00 (none:40) |
| night_porch_package | 1.00 |
