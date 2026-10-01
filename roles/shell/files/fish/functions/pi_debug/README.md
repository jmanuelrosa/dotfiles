# Pi debugging

`pi_debug` launches Pi with Cursor SDK failure-detail capture enabled.
`pi_last_error` prints the latest captured failure message and stack.

```fish
pi_debug
pi_last_error
```

Captured errors live under `~/.pi/agent/cursor-sdk-debug/sessions/`.
The reader requires `jq` and reports when no capture exists.
