# clean_docker

Stops all Docker containers, then prunes images, build cache, and volumes.
This can remove persistent container data.

```fish
clean_docker
```

Requires a running Docker daemon and the configured Docker CLI.
The function has no dry-run option; Docker's own prompts govern pruning.
