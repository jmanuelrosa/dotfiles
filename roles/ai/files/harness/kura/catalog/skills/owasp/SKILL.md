---
name: owasp
description: >-
  The OWASP Cheat Sheet Series distilled into read-only checks, one reference per security topic, each check tagged with the staff-engineer seat that owns it.
  Use when implementing, reviewing, or assessing code that touches authentication, MFA or passkeys, sessions and cookies, JWT, OAuth or SAML, authorization and tenancy,
  injection, XML or deserialization, XSS and CSP, CSRF, clickjacking and cross-origin, security headers, TLS and web caching, third-party scripts,
  REST, GraphQL, gRPC, WebSockets or webhooks, SSRF, file upload, cryptography and keys, secrets, security logging and error handling, abuse, bots and DoS,
  supply chain and dependencies, CI/CD, containers and Kubernetes, cloud, IaC and serverless, network segmentation and microservices,
  LLMs, RAG, AI agents and MCP, mobile apps, privacy and payments, threat modeling and secure code review,
  or a Java, .NET, C/C++, PHP, Python, Ruby or Node.js stack.
  Read only the reference files whose triggers match.
---

# OWASP cheat sheets

Every actionable recommendation of the OWASP Cheat Sheet Series, rewritten as a check and grouped by surface, one reference file per topic.
This skill is a router: match the change or the assessed surface against the trigger table, read only the files that fire, and within them only the sections that apply.

## How to use it

- **Implementer seats** read the files their row in the ownership table names, plus any trigger-table row the brief fires, and act on the items whose `Owner:` is their own seat.
  An item owned by another seat is not yours to implement: name it in the completion report as a cross-slice dependency.
- **The security advisor** reads every file whose trigger fires and assesses every item regardless of owner; the owner tag tells it which seat a finding routes to.
- **A reviewer** uses the owner tag to route each finding, and the check text as the verification bar.
- The seat's own failure-mode checklist stays its gate for `done`.
  These references are the depth behind it: a seat checklist names the failure class, the matching file here lists every recommendation OWASP makes for it.
- An item that recommends adding a library, a new dependency, or a breaking change to a shared API is a recommendation, not permission: it goes to the caller as `needs-decision`, as the global skill-precedence rules require.
- Where a check names a published value (an algorithm, a cost parameter, a header value), the value comes from the cited sheet; prefer the project's stricter value when it already has one.

## Ownership by seat

| Seat | Read first when the brief touches its surface |
|---|---|
| `backend` | tokens-and-federation, authentication, injection, rest-and-webhooks, abuse-dos-and-business-logic, mfa-passkeys-and-transaction-signing, xml-and-deserialization, authorization, graphql-grpc-and-websockets, sessions-and-cookies, logging-and-error-handling, file-upload, ssrf, the matching `stack-*` file |
| `frontend` | client-code-and-third-party, xss-and-csp, cross-origin-and-browser, stack-nodejs-and-nextjs for Next.js, http-headers-tls-and-caching |
| `mobile` | mobile, mfa-passkeys-and-transaction-signing, tokens-and-federation (native-app redirects) |
| `desktop` | stack-dotnet for .NET clients, cloud-and-infrastructure (thick-client database access); `frontend`-owned items apply to the renderer content a desktop app ships |
| `database` | injection, multi-tenancy, cloud-and-infrastructure (database section) |
| `data` | llm-prompt-injection-and-rag (ingestion), cryptography-and-keys (crypto-erasure) |
| `cloud` | cloud-and-infrastructure, secrets-management, cryptography-and-keys, tokens-and-federation (workload identity), network-zero-trust-and-microservices |
| `platform` | containers-and-kubernetes, ci-cd, stack-c-toolchain for native code, supply-chain-and-dependencies, secrets-management |
| `dx` | supply-chain-and-dependencies, ai-agents-and-mcp (AI coding tools) |
| `sre` | logging-and-error-handling, abuse-dos-and-business-logic |
| `qa` | authorization-testing |
| `gtm` | client-code-and-third-party |
| `architect` | secure-sdlc, network-zero-trust-and-microservices, authorization, multi-tenancy, plus any trigger row the design fires (its items also sit in embedded-and-vehicles, cryptography-and-keys, abuse-dos-and-business-logic, authentication, ai-agents-and-mcp) |
| `security` | every file whose trigger fires |

## Trigger table

| The change or assessed surface touches... | Read |
|---|---|
| Login, credential checks, password storage or reset, security questions, credential stuffing defenses, email verification | [references/authentication.md](references/authentication.md) |
| MFA factors and recovery, passkeys and WebAuthn, step-up or transaction signing | [references/mfa-passkeys-and-transaction-signing.md](references/mfa-passkeys-and-transaction-signing.md) |
| Session ids, cookies and their attributes, session lifetime, logout, cookie theft | [references/sessions-and-cookies.md](references/sessions-and-cookies.md) |
| JWT, OAuth 2.0 and OIDC, SAML, service-to-service identity propagation, workload identity federation | [references/tokens-and-federation.md](references/tokens-and-federation.md) |
| Permission checks, roles and policies, object ids from requests, mass assignment, authorization decisions in responses | [references/authorization.md](references/authorization.md) |
| Tests or CI jobs that prove authorization: access matrices, regression suites, automation | [references/authorization-testing.md](references/authorization-testing.md) |
| Tenant isolation in data, caches, queues, storage, compute, or admin tooling | [references/multi-tenancy.md](references/multi-tenancy.md) |
| Queries, shell commands, LDAP, XPath, template rendering, or other interpreters built from input; input validation | [references/injection.md](references/injection.md) |
| XML parsing, schemas, SOAP payloads, native or polymorphic deserialization | [references/xml-and-deserialization.md](references/xml-and-deserialization.md) |
| HTML or DOM output of untrusted data, sanitization, CSP, DOM clobbering, prototype pollution | [references/xss-and-csp.md](references/xss-and-csp.md) |
| CSRF, framing and clickjacking, cross-site leaks, postMessage, CORS, web storage, redirects and forwards | [references/cross-origin-and-browser.md](references/cross-origin-and-browser.md) |
| Response security headers, HSTS, TLS configuration, CDN or reverse-proxy caching | [references/http-headers-tls-and-caching.md](references/http-headers-tls-and-caching.md) |
| Third-party scripts and tags, micro-frontends, browser extensions, client-side JavaScript or TypeScript hardening | [references/client-code-and-third-party.md](references/client-code-and-third-party.md) |
| REST endpoints, SOAP or XML web services, outgoing or incoming webhooks | [references/rest-and-webhooks.md](references/rest-and-webhooks.md) |
| GraphQL schemas and resolvers, gRPC services, WebSocket endpoints | [references/graphql-grpc-and-websockets.md](references/graphql-grpc-and-websockets.md) |
| Server-side fetches of URLs or hosts derived from input | [references/ssrf.md](references/ssrf.md) |
| File upload, storage of user files, serving user files back | [references/file-upload.md](references/file-upload.md) |
| Encryption at rest, hashing for integrity, random numbers, key generation, rotation and storage, post-quantum migration | [references/cryptography-and-keys.md](references/cryptography-and-keys.md) |
| Secret storage, injection into apps or CI, rotation, detection of leaked secrets | [references/secrets-management.md](references/secrets-management.md) |
| Security event logging, log content and protection, exception handling, error responses | [references/logging-and-error-handling.md](references/logging-and-error-handling.md) |
| Rate limits, resource limits, bots and automation abuse, business-logic flows, abuse cases | [references/abuse-dos-and-business-logic.md](references/abuse-dos-and-business-logic.md) |
| Dependency manifests and lockfiles, npm packages, SBOMs, vulnerable dependency handling, provenance | [references/supply-chain-and-dependencies.md](references/supply-chain-and-dependencies.md) |
| CI/CD pipelines, GitHub Actions workflows, runners, deploy credentials | [references/ci-cd.md](references/ci-cd.md) |
| Dockerfiles and images, Node.js containers, Kubernetes manifests, Helm, cluster configuration | [references/containers-and-kubernetes.md](references/containers-and-kubernetes.md) |
| Cloud architecture, IaC, serverless functions, DNS and subdomains, database server hardening | [references/cloud-and-infrastructure.md](references/cloud-and-infrastructure.md) |
| Network segmentation, zero-trust access, microservice auth and architecture documentation | [references/network-zero-trust-and-microservices.md](references/network-zero-trust-and-microservices.md) |
| LLM prompts and output handling, RAG pipelines and vector stores, model operations, AI ad systems | [references/llm-prompt-injection-and-rag.md](references/llm-prompt-injection-and-rag.md) |
| AI agents and tool use, MCP servers or clients, agent execution evidence, AI-assisted coding | [references/ai-agents-and-mcp.md](references/ai-agents-and-mcp.md) |
| iOS, Android, or cross-platform mobile apps; certificate or public-key pinning | [references/mobile.md](references/mobile.md) |
| Personal data and user privacy, payment gateway integration, AML and sanctions screening for agent payments | [references/privacy-and-payments.md](references/privacy-and-payments.md) |
| Threat modeling, attack surface analysis, secure design, code review practice, vulnerability disclosure, legacy apps, virtual patching | [references/secure-sdlc.md](references/secure-sdlc.md) |
| Vehicle or drone software and their control links | [references/embedded-and-vehicles.md](references/embedded-and-vehicles.md) |
| Java, JAAS, Bean Validation | [references/stack-java.md](references/stack-java.md) |
| .NET and ASP.NET | [references/stack-dotnet.md](references/stack-dotnet.md) |
| C or C++ build toolchains, compiler and linker hardening | [references/stack-c-toolchain.md](references/stack-c-toolchain.md) |
| PHP configuration, Laravel, Symfony | [references/stack-php.md](references/stack-php.md) |
| Django, Django REST Framework, FastAPI | [references/stack-python.md](references/stack-python.md) |
| Ruby on Rails | [references/stack-ruby-on-rails.md](references/stack-ruby-on-rails.md) |
| Node.js servers, Next.js | [references/stack-nodejs-and-nextjs.md](references/stack-nodejs-and-nextjs.md) |

A typical backend change fires two to four rows plus its `stack-*` file; a whole-repo security assessment fires most of them.
Read all that fire; skip the rest.
The `stack-*` files carry only framework-specific settings and point back to the topic files for everything generic.

## How each reference is structured

- `When to read:` repeats the trigger row; `Sources:` links every OWASP sheet the file distills.
- Sections group items by sub-topic, most severe first; files over ~100 lines open with a contents list.
- Each item is a bold, mechanism-first rule name, the recommendation in one or two sentences, a `Check:` performable by reading code, config, or a diff, the owning seat, and the source sheet.
- A pointer item (`See <file>.md for ...`) marks a recommendation that lives in another file, so each one is stated once.

Derived from the [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/), licensed CC BY-SA 4.0; the snapshot and per-sheet mapping are in `SOURCES.md`.
