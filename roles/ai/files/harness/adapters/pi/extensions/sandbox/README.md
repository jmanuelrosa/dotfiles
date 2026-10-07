# Sandbox adapter

Loads the installed `pi-sandbox` package through a wrapper because upstream has no per-command exemptions.
The package remains installed, but its standalone extension is disabled in `settings.json` so only this adapter registers its tools and handlers.

`adapter.toml` owns `sandbox.excludedCommands`, rendered into `sandbox.json` by `make harness`.
Only direct `gcloud` and `bq` calls run through Pi's local bash implementation.
Commands containing shell operators, redirections, substitutions, escapes or newlines remain sandboxed, including pipelines and chained commands.
The wrapper skips only upstream's sandbox checks for those calls; the shared cloud read-only gate and Pi's permission system still inspect the original `bash` tool call.
Read, write, edit, other bash commands, sandbox controls and session lifecycle remain upstream-owned.

The AI role links this extension through `PI_EXTENSIONS`.
After provisioning with `make run-role ROLE=ai`, restart Pi to load the adapter.
No credential directories or Google domains are added to the sandbox allowlists.
