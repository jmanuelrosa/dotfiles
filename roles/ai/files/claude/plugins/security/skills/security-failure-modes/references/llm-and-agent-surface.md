# LLM and agent surface

When to read: the assessed surface includes LLM API calls, agents and tool-use loops, MCP servers or clients, or rendering of model output.

## Failure modes to rule out

Each item is a check.
An item you could not verify goes in the Not assessed section; silence is never read as safety.

- **Prompt injection unmodeled as an entry point.** Any untrusted content reaching a prompt (user text, retrieved documents, web pages, emails) can steer the model; this is the top of the OWASP LLM Top 10 for a reason.
  Check: trace every string that reaches a prompt back to its origin; untrusted content mixed with instructions is a finding unless the model's downstream effects are constrained to safe operations.
- **Model output executed or rendered raw.** Output fed to eval, shell, SQL, or the DOM is injection with extra steps; the model is not a trusted author.
  Check: find every consumer of model output and confirm it is treated as untrusted input: parsed, validated, and encoded like any external data.
- **Tools with more authority than the loop needs.** An agent whose tools can write, delete, or reach the network turns any successful injection into those actions.
  Check: inventory the tools each agent or tool-use loop can call and their scopes; confirm authorization is enforced inside the tool implementation, server-side, never by prompt instructions, and that high-impact actions sit behind human confirmation.
- **The confused-deputy agent.** An agent acting for many users under one shared privileged identity erases the authorization boundaries the rest of the app enforces.
  Check: trace whose credentials tool calls execute under; actions touching user data carry per-user scoping, not the agent's ambient privilege.
- **MCP servers and plugins as unvetted dependencies.** Third-party MCP servers and model plugins are supply chain plus live integration: they see prompts and can return injected content.
  Check: enumerate configured MCP servers and plugins; their provenance and pinning get the supply-chain-and-build treatment, and their responses, tool descriptions, and metadata are treated as untrusted input.
- **Secrets and personal data in prompts.** Prompt assembly that interpolates secrets or inventoried personal data ships them to a third-party processor and its logs.
  Check: read the prompt-construction code against the sensitive-field inventory from data-protection-and-leakage; secrets never belong in prompts.
- **Privileged instructions in client hands.** System prompts or role claims accepted from the client let callers rewrite the rules the loop runs under.
  Check: confirm system prompts and privileged instructions are assembled server-side; anything client-supplied enters only as data.
- **No record of what the model did.** Agent actions without logs (which tool, what arguments, on whose behalf) make model-driven incidents unreconstructable.
  Check: agent and tool-use actions produce attributable logs like any privileged mutation; the gap routes through detection-and-evidence.
- **Unbounded loops and spend.** An agent loop without iteration, recursion, or budget caps is self-inflicted denial of service and an amplifier for any injection.
  Check: locate the iteration, depth, and spend limits in the loop configuration; their absence is a finding.

## Escalation triggers (report immediately)

- A traced path from untrusted content through a prompt to a state-changing tool call with no validation between: treat it as an actively exploitable P0 shape; lead the report with it.
- The brief drifting toward crafting adversarial prompts against a live system: exploitation is out of scope (also a hard rule); the evidence is the traced path.

## What good looks like

- Instructions and data are separated at prompt assembly, model output is validated, and tools enforce authorization independent of anything the prompt says.
- Agent identity mirrors the calling user's scopes, and every tool call is logged attributably.
- MCP and plugin integrations are pinned, vetted, and treated as untrusted input sources.
