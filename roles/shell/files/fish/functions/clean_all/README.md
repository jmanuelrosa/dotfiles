# clean_all

Runs the Homebrew, Mole system, and Node cleanup aliases in sequence.
It does not invoke Docker or AI cleanup.

```fish
clean_all
```

Requires the [shell aliases](../../conf.d/aliases/README.md).
Node cleanup can delete dependency directories and working-directory lockfiles; inspect [clean_node](../clean_node/README.md) before running it.
