# local-ai

Reproducible local coding models for the 24 GB Apple-silicon workstation. The tool
downloads immutable, SHA-256-verified GGUF artifacts with resumable range requests
(and verifies the official Ollama manifest and blob for Devstral),
imports 32K and 64K Ollama
profiles, runs the same TypeScript agent tasks against every finalist, and points the
stable Pi model names at the winners.

Stable aliases use the non-reasoning API shape shared by every finalist; the pinned
benchmark profiles retain each model's native reasoning metadata.

```console
local-ai catalog
local-ai install                  # all three finalists; downloads about 48 GB
local-ai benchmark                # selects local-code-quality and local-code-fast
local-ai compare-runtime          # keep Ollama unless direct llama.cpp wins by 15%
local-ai doctor
local-ai pi quality 32k           # equivalent to the default plain `pi`
local-ai pi fast 32k
local-ai pi quality 64k
```

The benchmark weights correctness 50%, tool-loop execution 25%, throughput 15%, and
loaded memory 10%. A model must pass every fixture and complete the expected tool loop
to be selectable. `local-code-quality` is the highest-scoring accepted candidate;
`local-code-fast` is the fastest accepted candidate within 15 points of it.
The benchmark saves correctness results but refuses to change aliases when Metal is
not visible, preventing a sandbox or VM from choosing a winner using CPU-only timings.

Normal operation is local-only. Pi starts with `PI_OFFLINE=1`; Ollama binds only to
`127.0.0.1`, has cloud features disabled in both its server policy and launch-agent
environment, uses Flash Attention with a Q8 KV cache, and keeps at most one model
loaded. Internet access is needed only by `local-ai install` for the pinned downloads.

Model weights and results live under
`~/Library/Application Support/local-ai/`. The catalog, Pi profiles, service policy,
and selection machinery live here in dotfiles. The 32K profile is the default; 64K is
explicit because its KV cache needs materially more unified memory.
