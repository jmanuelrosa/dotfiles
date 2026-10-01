# clean_node

Deletes discovered `node_modules` directories, clears npm and Bun caches, and removes lockfiles in the working directory.
Run it only from the tree you intend to clean.

```fish
clean_node
```

Discovery uses the `find` alias backed by `fd`, so the [aliases snippet](../../conf.d/aliases/README.md) must be loaded.
The function has no dry-run or confirmation step.
