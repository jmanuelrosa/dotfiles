# Server-side tagging

When to read: the brief or diff touches server container clients and tags, request claiming, transport, logging, statefulness, or first-party server-set cookies.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Silent event drop.** A server tag's outbound call (`sendHttpRequest`, `sendPixel`) is not awaited, a non-2xx response is ignored, or `returnResponse` fires before in-flight sends resolve, so the client reports success while the event never reached the destination.
  Check: outbound calls are awaited and their status checked; the client sets its response status and calls `returnResponse` only after every dispatch has completed, so nothing is cut off mid-flight.
- **Request claimed wrong.** A custom client that claims paths it should not steals requests from other clients; one that never calls `claimRequest`, or claims the wrong condition, lets the request 400 and the event drop.
  Check: `claimRequest` is reached for exactly the client's request surface by path and method; overlap with other clients is resolved deliberately.
- **State assumed across requests.** In-memory caches or per-user globals break under horizontal scaling, where each request may hit a different instance.
  Check: nothing relies on in-process state between requests; anything durable goes to an external store or rides the request and response.
- **Personal data in logs.** `logToConsole` or error logging writes emails, tokens, or full payloads into Cloud logging, creating a second uncontrolled copy of personal data.
  Check: logs carry no personal data or secrets; payload logging is redacted or gated to non-production.
- **First-party cookie set wrong.** Server identity cookies missing `HttpOnly`, `Secure`, or the correct `SameSite`, or scoped to the wrong domain, get capped by ITP or fail to send.
  Check: server cookies use `HttpOnly` and `Secure`, correct `SameSite`, and the registrable domain the collection endpoint shares with the site; the custom domain maps by A/AAAA record, not a CNAME that ITP treats as third-party.
- **Endpoint not first-party.** The tagging server runs on a domain blockers treat as third-party, or on the default vendor host, undercutting the reason to go server-side.
  Check: the collection endpoint is a first-party subdomain of the site (custom domain mapped), not the vendor default, where durability is the goal.
- **Phantom container.** A tagging server is deployed pointing at an empty or never-published container: health checks pass and it returns 200, but every event 404s and is lost.
  Check: the deployed server maps to a published container version, and a live event is confirmed received, not just a healthy status.
- **Secrets inlined.** Destination tokens or keys are hardcoded in a tag or template instead of the server container's secret mechanism.
  Check: destination credentials come from server-container variables or secrets, never literal strings in a tag.
- **Cost-blind fan-out.** Every incoming request fans out to many destination calls with no timeout or concurrency thought, running up latency and hosting cost.
  Check: outbound calls have timeouts; per-request fan-out and its cost are considered; heavy work is justified.

## Escalation triggers (`needs-decision`)

- A change that requires provisioning, scaling, or migrating the tagging server, its custom domain, or its hosting (cloud and platform seats execute; also an ask-first boundary in the agent).
- Adding a new server-side destination that receives personal data, or a new outbound endpoint.

## What good looks like

- Clients claim precisely their surface; tags await dispatch and handle failure; the server is stateless per request.
- First-party, `HttpOnly` and `Secure` cookies on the right domain; no personal data or secrets in logs.
- Outbound calls are bounded and credentialed through the container's secret mechanism.
