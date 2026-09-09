# Forkline Delivery Lab demonstration

Stock synthetic narration. Actual local application recording.

A blockchain order can be confirmed when it enters a queue, then disappear before the worker sends anything. Forkline now tests that gap using a real local application: a SQLite outbox and an HTTP ticket receiver with its own database. These are fixture tickets, not real admission or real funds.

Both workers have observed the same order and waited for three confirmations. Both queue the same delivery. The comparison consumer checks only here. Forkline also checks again immediately before dispatch, against its latest observed head.

Now the branch changes. Dispatch the queued work. The comparison consumer issues one ticket backed by an orphaned event. Forkline holds its queued command and issues none. Restarting the workers preserves both facts. This catches the before dispatch case; it is not a promise that a later reorganization cannot happen.

The second case is harder. The receiver commits the ticket, but we deliberately drop the HTTP acknowledgement. The worker records an uncertain outcome. Zero acknowledgements does not mean zero tickets. A blind retry could repeat an external action.

Reopen the worker databases, then change the branch. Reconcile by reading the receiver receipt, not by issuing another ticket. Forkline preserves the one completed action and latches an incident. The receipt survives even though its supporting event disappeared.

A replacement order becoming eligible does not clear that incident. Neither does the old branch returning. The operator has a receipt and a reason to investigate, rather than a silently erased delivery.

The source includes this live local lab, the compiled contract fixture, database files, and a process crash regression. The hosted page replays those executed records. The next step is a developer pilot and a maintained live node adapter. This is a reproducible integration test, not consensus finality or an exactly once guarantee for arbitrary services.