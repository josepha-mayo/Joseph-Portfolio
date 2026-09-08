# SunQueue Shift Sheet demonstration

Actual app actions. Synthetic scenario and forecast-derived conditions; no real work was run. Stock Kokoro af_heart synthetic narration, not a cloned voice.

A solar powered workshop can have enough energy for the day, but run its work at the wrong hour. SunQueue plans the same jobs around daylight, while protecting a battery reserve. The important part is what happens afterwards: less energy is not a saving if the work never finished.

Start with the work, not an electrical guess. Six hundred and fifty watts for two hours is one point three kilowatt hours. The job builder makes that conversion visible. Existing jobs, time windows and supply assumptions remain editable. Background demand excludes these jobs, so their energy is not counted twice.

Run the actual scheduling worker. It keeps every requested job and tests both the forecast and a reduced solar case. This synthetic example moves evaluation, training and processing into the daytime. These are calculated results, not measurements from a real workshop. The earlier starting baseline uses the same jobs and equipment.

Choose the work date, the clock time of the first slot, and the site UTC offset. Shift Sheet turns the selected slots into readable start and finish times. Each card includes operating watts, job energy and its deadline. A dated handoff is easier to follow than a table of slot numbers.

Download a readable work sheet or a tentative calendar file. Nothing is added to a calendar account and no equipment starts automatically. Review the current conditions before running anything. When a plan changes, remove older calendar entries yourself. These files are a manual handoff, not a live controller.

Now record what happened. Every job starts as not yet reported. Here I enter the planned intervals as completed, and use the original forecast as clearly labelled example conditions. The same energy simulator compares the recorded run with the frozen plan and early starting baseline. Equal end battery energy is checked too.

Suppose training stopped after one hour instead of completing three. That hour still consumes eight hundred and fifty watt hours in the model. The job is not counted complete. The report now says two of three jobs finished, and blocks the equivalent work savings claim. Skipped work, late finishes and energy shortfalls stay visible.

Save the shift and reported run, then reopen them after reloading the page. The original plan, date, conditions and incomplete outcome return together. Recompute the comparison rather than trusting stored totals. Changing an outcome invalidates the previous report. This remains operator supplied information, not authenticated meter data.

The architecture is a small, local browser application: a bounded scheduling worker, one energy simulator, and a separate run interval ledger. It needs no account, API key or cloud inference. The current limit is four jobs on one machine in whole hours. Independent reference checks and failure cases are included with the source.

The intended first users are small solar powered labs and workshops. The commercial hypothesis is paid setup and data import support around a free local planner, not an existing subscription business. The next validation is an authorized site pilot comparing completed work, grid energy and terminal battery reserves. No pilot or measured saving is claimed. Plan the work, record the work, then compare honestly.
