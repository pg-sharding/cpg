# Original packet dependency restoration

The first local input-copy attempt stopped before building or sending inputs:
`publication-r1/followup-r3/gin-am-micro.c` is absent in the old packet.
The failed partial copy is retained as `inputs-attempt0-missing-module/`.
There are zero build/timing observations from this attempt.

The old packet does contain the corrected module at
`publication-r1/runtime-r2/gin-am-micro.c`. Its 2119 bytes and SHA256
`add8e8b481a7d0cc6d1ea2c075fbe1f74cbed647accec5da432244ed51fb1bb6`
exactly match the original executed R3 screen and full-SQL frozen-input
receipts. Copy that file to the expected R3 location in the new input bundle.
No C source, SQL, protocol, timing or analysis algorithm changes.
