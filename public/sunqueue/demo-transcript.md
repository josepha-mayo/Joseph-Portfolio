# SunQueue demonstration

Actual recorded application actions with disclosed stock Kokoro af_heart neural narration. Synthetic inputs, no real equipment or measured savings. Edited audio/video, not a continuous human recording.

## The same work. A better hour.

A solar powered lab can have enough energy across the whole day and still run short at the wrong hour. Flexible work makes that a scheduling problem. Sun Queue asks when these jobs should run so they finish on time without using the protected battery reserve. This is an original synthetic example, not a measurement of a real installation.

## Make the constraints visible.

The example has three jobs on one shared machine: model evaluation, a training experiment, and dataset processing. Each has a duration, a power requirement, an earliest start, and a deadline. Hourly inputs describe solar energy, background load, and grid availability. Storage settings include conversion losses, charge and discharge limits, a protected reserve, and an end of day minimum. That last requirement matters: the planner cannot call an emptied battery a saving.

## Run the real search.

The reduced solar case uses sixty five percent of the forecast. That is a chosen stress scenario, not a weather confidence level. The planner checks candidate start times against both cases. Here it evaluates five hundred and thirteen complete schedules. Its selected plan uses no grid energy in the reduced solar case, compared with one thousand eight hundred and fifteen watt hours for the early start baseline.

## Check what stayed the same.

All three jobs still finish inside their windows. The equipment inputs have not changed. Both plans respect the modeled constraints and end with at least their starting battery energy. Switch between forecast and reduced solar to inspect the hourly flows. Green is solar, blue is total demand, and amber is grid supply. The numbers describe this supplied model. They are not measured savings or a guarantee about another system.

## An impossible plan must stay impossible.

A useful planner must also say when the inputs do not work. Set the load limit to fifty watts and search again. Even the background demand exceeds that limit. There is no feasible recommendation, and the export is unavailable. Sun Queue does not silently remove a difficult job. It also distinguishes a completed search from a search that reached its limit without establishing the answer.

## Keep the record reviewable.

Restore the example and export the real plan, then save the schedule as a C S V file. The detailed record contains the inputs, their fingerprint, both solar cases, hourly energy flows, and the baseline. Changing an input removes the old plan and disables its exports. Reopening the saved record verifies the input fingerprint, ignores imported results, and requires a fresh search. A saved output cannot declare itself correct.

## Work with daylight. Keep the reserve.

Sun Queue is a planning tool, not an inverter controller. It uses whole hour averages and a fixed battery dispatch rule. It does not predict the weather, model electrical surges, or control a G P U. Its source and tests are available for inspection, including a separate Python solver. The next validation step is authorized measured equipment data. The goal is to move flexible work toward available daylight while keeping the reserve and the comparison visible.
