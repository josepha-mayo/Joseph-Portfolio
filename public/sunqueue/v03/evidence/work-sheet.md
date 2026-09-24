# SunQueue shift sheet

Work date: 2026-09-09. All clock times use UTC+01:00.
Slot 0 starts at 2026-09-09 06:00. Scenario labels are not used as calendar timestamps.

**Tentative plan, not device control or proof of work.** Review equipment limits and current conditions before starting.

Scenario: Synthetic workshop day, not a measurement of Joseph's equipment

## Model evaluation
Start 2026-09-09 10:00; finish 2026-09-09 12:00 (UTC+01:00).
Slots 4 to 6; 650 W for 2 hours = 1.300 kWh of modeled job energy.
Finish-by window: 2026-09-09 16:00.

## Training experiment
Start 2026-09-09 12:00; finish 2026-09-09 15:00 (UTC+01:00).
Slots 6 to 9; 850 W for 3 hours = 2.550 kWh of modeled job energy.
Finish-by window: 2026-09-09 18:00.

## Dataset processing
Start 2026-09-09 15:00; finish 2026-09-09 16:00 (UTC+01:00).
Slots 9 to 10; 400 W for 1 hours = 0.400 kWh of modeled job energy.
Finish-by window: 2026-09-09 20:00.

## Before starting
Check the current solar, background demand, reserve and supply assumptions. A changed schedule needs a new model check. The app cannot detect physical conditions.

Battery reserve: 600 Wh. End minimum: 1800 Wh. AC load limit: 2000 W.

## After the shift
Record each job as completed, stopped or not run, plus its real hourly interval. Use a supplied profile to compare the recorded run. An unreported outcome is not assumed complete.

Frozen plan: 921f6abe28a4ce294e7e9450256633b8e29bf29539772912f7b19d4e5472ae8b
Fingerprints identify supplied bytes, not the operator, true measurements or a certified result.
