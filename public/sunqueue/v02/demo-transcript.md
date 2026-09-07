# SunQueue Replay and business demonstration

Stock Kokoro af_heart neural narration. Actual recorded app actions; original synthetic profiles. Edited recording, not a human voice or field study.

## Who it is for

Sun Queue is for a small solar powered workshop or compute lab with flexible jobs and an unreliable grid. The first customer hypothesis is narrow: an operator who already has solar, can move a few jobs, and needs to know whether those changes help without missing deadlines. This working prototype is not connected to real equipment. All the values in this demonstration are synthetic, and no customer revenue or field savings are claimed.

## Same work and explicit limits

Each job has a duration, power demand, earliest start and deadline. The same three jobs must finish on one machine. The supply profile includes hourly solar, background demand and grid availability. Battery settings include efficiency losses, power limits, a protected reserve and an end of day minimum. These constraints matter more than a green headline. A planner should not claim a saving just because it dropped the difficult job or spent tomorrow's stored energy.

## Run the actual planner

The search runs in a browser worker. It enumerates non overlapping start times and simulates energy flow in both the forecast and a chosen reduced solar case. Here it evaluates five hundred and thirteen schedules. In the reduced solar example, the selected schedule models zero grid energy, versus eighteen hundred and fifteen watt hours for the early start baseline. Both complete the same requested work in the model. The displayed optimum is limited to the finite model and fixed battery dispatch rule.

## A reproducible handoff

The operator can export the schedule and its full calculation record. The source, input fingerprint, two scenarios and baseline remain inspectable. Changing an input clears old results and blocks old exports. Imported outputs are not trusted. The architecture is intentionally small: a pure JavaScript simulation engine, a bounded search inside a worker, and a local interface. There is no inference bill, backend account, telemetry or equipment command. The tradeoff is limited scale, not a claim of enterprise orchestration.

## Freeze before replay

The new Replay Desk addresses the next question: what happens when the energy profile is different? First freeze the chosen job starts. Then provide an hourly C S V containing solar, background demand and grid limits. Replay uses those fixed starts. It does not quietly optimize again after seeing the new data. Copying the forecast is a consistency check, not validation against measurements. Real site data can use the same format, but its origin and calibration must be established separately.

## Show the failure as well

Now load an explicitly synthetic all cloud case. The frozen schedule cannot meet the supplied service and battery requirements. The baseline fails too. The interface shows the unmet energy and endpoint violations, and refuses a comparable savings claim. It also suppresses that claim when both plans pass but the proposed schedule ends with less stored energy. This is important: a smaller grid number is not automatically equivalent service or a better energy outcome.

## Save without trusting the result

Save the replay project and reopen it. The file preserves the frozen inputs, chosen starts and replay profile with integrity fingerprints. Reopening ignores saved outcomes and requires recomputation. Changing either the profile or the planning inputs invalidates the old export. This is reproducible model replay, not a signed measurement or a guarantee of hardware safety. Testing includes an independent Python implementation of the declared model and browser checks of the actual controls and downloads.

## A business hypothesis to test

The proposed route is paid setup and data replay for small solar powered sites, while the local planner remains free. Test pricing is twenty five dollars for setup and five dollars monthly per site. With an illustrative two dollar monthly support allowance, ten subscribers contribute thirty dollars before overhead, taxes and customer acquisition. These are assumptions, not a market study or existing sales. First recruit a few authorized pilots, compare the same completed work and terminal energy, and measure whether the benefit exceeds the fee. If it does not, change the product before charging.
