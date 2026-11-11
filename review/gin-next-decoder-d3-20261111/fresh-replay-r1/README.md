# Fresh Linux frontdoor — static validation only

Use `replay.py --inputs PACKET --git EXISTING_B72_REPOSITORY --output NEW_SHORT_ROOT` to run four fresh matched builds and the finite ordinary gate. Exact commands, flags, dependencies, data creation and the separate timing protocol are in `../REPRODUCE.md`. `--source-archive` is an alternative local source route; all 7726 raw baseline file hashes are verified. No network fetch or package installation is performed.

This portable frontdoor has passed local AST/help and all 40 frozen input bindings. It has not been executed as a new Linux build or runtime replay. Actual historical builds and qualification used the separately recorded root scripts.

The revised wrapper explicitly installs Python's default SIGINT handler. On interruption it sends SIGINT only to the owned child controller, allows 480 seconds for its `finally` cleanup, then records `cleanup_timeout` and a preserved failure if the child is still running. It does not force-kill the controller group. Independent live proof remains required after any failed attempt. Builder and qualifier ownership checks and their own command/client cleanup remain unchanged. Interruption behavior is source-reviewed, not runtime-tested.

The previous static-only wrapper and receipt remain under `historical-static-r1/`; `STATIC-REVIEW-r2.json` identifies the current helper. The fresh frontdoor stops after ordinary qualification and cannot approve or start timing.
