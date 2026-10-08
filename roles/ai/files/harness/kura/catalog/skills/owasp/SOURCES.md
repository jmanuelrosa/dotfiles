# Sources

Every runtime reference distills sheets of the [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) (CC BY-SA 4.0).
The derived references carry the same licence.

## Snapshot

- Repository: `OWASP/CheatSheetSeries`, `cheatsheets/*.md`
- Commit: `29994dd8a2e6f50fa3d5607b046b54d7c6945afd` (2026-10-06)
- Sheets: 137, every one mapped below

## Sheet to reference map

| Reference | Checks | Sheets |
|---|---|---|
| `references/authentication.md` | 76 | Authentication, Authentication_Patterns, Password_Storage, Forgot_Password, Choosing_and_Using_Security_Questions, Credential_Stuffing_Prevention, Email_Validation_and_Verification |
| `references/mfa-passkeys-and-transaction-signing.md` | 53 | Multifactor_Authentication, Passkey_Security, Transaction_Authorization |
| `references/sessions-and-cookies.md` | 37 | Session_Management, Cookie_Theft_Mitigation |
| `references/tokens-and-federation.md` | 96 | JSON_Web_Token, OAuth2, SAML_Security, Identity_Propagation_Patterns, Workload_Identity_Federation |
| `references/authorization.md` | 54 | Authorization, Authorization_Decisions_And_Output_Handling, Authorization_Patterns, Authorization_Policy_And_Data_Distribution, Insecure_Direct_Object_Reference_Prevention, Mass_Assignment, Access_Control |
| `references/authorization-testing.md` | 18 | Authorization_Regression_Testing, Authorization_Testing_Automation |
| `references/multi-tenancy.md` | 50 | Multi_Tenant_Security |
| `references/injection.md` | 71 | Injection_Prevention, SQL_Injection_Prevention, Query_Parameterization, NoSQL_Security, LDAP_Injection_Prevention, OS_Command_Injection_Defense, XPath_Injection_Prevention, Server_Side_Template_Injection_Prevention, Input_Validation |
| `references/xml-and-deserialization.md` | 49 | XML_External_Entity_Prevention, XML_Security, Deserialization |
| `references/xss-and-csp.md` | 43 | Cross_Site_Scripting_Prevention, DOM_based_XSS_Prevention, DOM_Clobbering_Prevention, XSS_Filter_Evasion, Content_Security_Policy, Prototype_Pollution_Prevention |
| `references/cross-origin-and-browser.md` | 51 | Cross-Site_Request_Forgery_Prevention, Clickjacking_Defense, XS_Leaks, HTML5_Security, Unvalidated_Redirects_and_Forwards |
| `references/http-headers-tls-and-caching.md` | 59 | HTTP_Headers, HTTP_Strict_Transport_Security, Transport_Layer_Security, Transport_Layer_Protection, TLS_Cipher_String, Web_Cache_Security |
| `references/client-code-and-third-party.md` | 46 | Third_Party_Javascript_Management, Web_Frontend_Security, Micro_Frontend_Security, Browser_Extension_Vulnerabilities, JavaScript_and_TypeScript_Security |
| `references/rest-and-webhooks.md` | 60 | REST_Security, REST_Assessment, Web_Service_Security, Webhook_Security |
| `references/graphql-grpc-and-websockets.md` | 47 | GraphQL, gRPC_Security, WebSocket_Security |
| `references/ssrf.md` | 17 | Server_Side_Request_Forgery_Prevention |
| `references/file-upload.md` | 24 | File_Upload |
| `references/cryptography-and-keys.md` | 48 | Cryptographic_Storage, Key_Management, Post_Quantum_Cryptography |
| `references/secrets-management.md` | 41 | Secrets_Management |
| `references/logging-and-error-handling.md` | 36 | Logging, Logging_Vocabulary, Error_Handling |
| `references/abuse-dos-and-business-logic.md` | 67 | Denial_of_Service, Bot_Management_and_Anti-Automation, Business_Logic_Security, Abuse_Case |
| `references/supply-chain-and-dependencies.md` | 43 | Software_Supply_Chain_Security, Vulnerable_Dependency_Management, Dependency_Graph_SBOM, NPM_Security |
| `references/ci-cd.md` | 45 | CI_CD_Security, GitHub_Actions_Security |
| `references/containers-and-kubernetes.md` | 57 | Docker_Security, NodeJS_Docker, Kubernetes_Security |
| `references/cloud-and-infrastructure.md` | 43 | Secure_Cloud_Architecture, Infrastructure_as_Code_Security, Serverless_FaaS_Security, Subdomain_Takeover_Prevention, Database_Security |
| `references/network-zero-trust-and-microservices.md` | 34 | Network_Segmentation, Zero_Trust_Architecture, Microservices_Security, Microservices_based_Security_Arch_Doc |
| `references/llm-prompt-injection-and-rag.md` | 97 | LLM_Prompt_Injection_Prevention, RAG_Security, Secure_AI_Model_Ops, AI-Powered_Advertising_Systems_Security |
| `references/ai-agents-and-mcp.md` | 75 | AI_Agent_Security, MCP_Security, Verifying_Third_Party_Agent_Execution_Evidence, Secure_Coding_with_AI |
| `references/mobile.md` | 35 | Mobile_Application_Security, Pinning |
| `references/privacy-and-payments.md` | 30 | User_Privacy_Protection, Third_Party_Payment_Gateway_Integration, AML_Sanctions_AI_Agent_Payments |
| `references/secure-sdlc.md` | 38 | Threat_Modeling, Attack_Surface_Analysis, Secure_Product_Design, Secure_Code_Review, Vulnerability_Disclosure, Legacy_Application_Management, Virtual_Patching, Security_Terminology |
| `references/embedded-and-vehicles.md` | 22 | Automotive_Security, Drone_Security |
| `references/stack-java.md` | 34 | Java_Security, JAAS, Bean_Validation, Injection_Prevention_in_Java |
| `references/stack-dotnet.md` | 65 | DotNet_Security |
| `references/stack-c-toolchain.md` | 39 | C-Based_Toolchain_Hardening |
| `references/stack-php.md` | 55 | PHP_Configuration, Laravel, Symfony |
| `references/stack-python.md` | 57 | Django_Security, Django_REST_Framework, FastAPI_Security |
| `references/stack-ruby-on-rails.md` | 24 | Ruby_on_Rails |
| `references/stack-nodejs-and-nextjs.md` | 61 | Nodejs_Security, Nextjs_Security |

## Sheets with no or reduced extraction

- `Access_Control`: deprecation redirect to Authorization, no items.
- `Transport_Layer_Protection`: deprecation redirect to Transport Layer Security, no items.
- `TLS_Cipher_String`: deprecation redirect to Transport Layer Security, no items.
- `Injection_Prevention_in_Java`: redirect into Java Security, no items.
- `Security_Terminology`: glossary; its embedded rules are stated in injection, xss-and-csp and cryptography-and-keys.
- `XSS_Filter_Evasion`: payload catalog; defensive takeaways only.
- `Abuse_Case`: archived sheet; process items merged with Business Logic.
- `Logging_Vocabulary`: event catalog grouped into event families.
- `Error_Handling`: mostly per-framework samples; generic rules only.

## Extraction rules

- Every actionable recommendation became one item: a bold mechanism-first rule, a read-only `Check:`, one owner seat, and the source sheet.
- Dropped: background prose, attack walkthroughs, payloads, code samples, tool advertisements; a rule shown only in a sample was kept as a rule.
- Options a sheet presents as optional extras were left out or worded "where adopted".
- Recommendations several sheets make were merged and cite each; a recommendation whose home is another file is a `See <file>.md` pointer.
- Generic files name mechanisms, except where a sheet publishes a concrete value (algorithm, parameter, header, version floor); `stack-*` files name framework settings.
- The Abuse Case sheet asks for abuse-case IDs in code comments; that conflicts with the no-ticket-ids-in-comments rule, so the item requires the traceability record without prescribing comments.

## Refresh procedure

1. Download the current `cheatsheets/` directory and diff it against the recorded commit: `gh api repos/OWASP/CheatSheetSeries/compare/<recorded>...master --jq '.files[].filename'`.
2. Re-extract only the changed sheets into the reference that owns them in the map above; a new sheet joins the topic file whose surface it shares.
3. Keep the item shape and the owner vocabulary in `SKILL.md`; update the counts and the commit here.
