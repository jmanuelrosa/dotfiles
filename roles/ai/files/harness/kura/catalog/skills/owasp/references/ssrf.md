# Server-Side Request Forgery

When to read: the brief, diff, or assessed surface touches a server-side fetch of a user-influenced URL, host, or IP (avatar or image import, webhook or callback URL, link preview, PDF or HTML renderer, proxy, integration with an internal service), outbound HTTP client configuration, egress firewall rules, or cloud instance metadata settings.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Server-Side Request Forgery Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)

## Destination control at the application layer

- **Complete URL accepted from the user as the fetch target.** URLs are hard to validate and parsers can be abused, so the application does not accept whole URLs from users; where network information is genuinely needed it accepts only a valid IP address or domain name.
  Check: trace every outbound request whose URL, host, or IP derives from request input; flag any handler that passes a user-supplied URL string to an HTTP client, and change the input contract to an IP or domain name. Owner: `backend`. Source: SSRF Prevention.
- **Destination not matched against an allowlist of trusted applications.** When the callers are known (an internal HR system, a partner API), the IP or domain is compared against an explicit allowlist of every trusted application's IPv4 and IPv6 addresses and domain names using strict, case-sensitive string comparison; a denylist is not a substitute.
  Check: confirm an allowlist exists for the outbound feature and that the comparison is exact (no `contains`, prefix, or regex match) and covers both IPv4 and IPv6 entries. Owner: `backend`. Source: SSRF Prevention.
- **Request built from user-supplied URL components instead of the matched allowlist entry.** After the host matches, the request is constructed from the allowlist entry with a scheme, port, and path the application fixes itself; carrying the user's path or query through hands the next component something it must parse again.
  Check: read the request-building code after validation; flag reuse of the user's scheme, port, path, query, or userinfo, and rebuild from constants plus the matched entry. Owner: `backend`. Source: SSRF Prevention.
- **IP or domain format validated with ad hoc parsing.** Format validation runs first through a battle-tested library that is not fooled by hex, octal, dword, URL, or mixed encodings (IPs) and that performs no DNS resolution (domains), and the library's normalized output, not the raw input, is what gets compared to the allowlist or blocklist.
  Check: identify the IP and domain validators; flag hand-written regexes or `split('.')` parsing and any comparison that uses the raw input rather than the validator's parsed value. Owner: `backend`. Source: SSRF Prevention.
- **Validated hostname re-resolved at connect time (DNS rebinding).** Domain allowlisting alone does not stop DNS rebinding: the resolved A and AAAA addresses are validated against permitted networks and the client connects only to a validated address, with no second unchecked lookup between validation and connection.
  Check: confirm the HTTP client is pinned to the validated IP (custom resolver, connect-to-address option) while the original hostname is kept for the `Host` header, TLS SNI, and certificate verification; flag code that validates `resolve(host)` and then calls `get(url)`. Owner: `backend`. Source: SSRF Prevention.
- **Destination policy skipped on retries, fallbacks, or redirects.** Following redirects lets a validated destination bounce the request anywhere, and retries or fallback connections can bypass the check, so redirect following is disabled and the destination policy applies to every connection attempt.
  Check: inspect outbound client options for redirect following (default on in many clients) and retry or fallback paths; set redirects off and route retries through the same validated-address connection. Owner: `backend`. Source: SSRF Prevention.
- **URL parsed by components that disagree on the host.** When a URL crosses a service boundary as a string and is parsed again, two parsers (for example a WHATWG parser and an RFC 3986 parser) can read different hosts from the same bytes; a URL whose host is not read identically by every parser in play is rejected rather than reconciled.
  Check: list every parser that sees the URL (gateway, validator, HTTP client, downstream service); flag validation done with one parser and fetching done with another, and add a rejection when hosts differ or when backslashes or `@` appear in the authority. Owner: `backend`. Source: SSRF Prevention.
- **Scheme or protocol taken from input.** SSRF is not limited to HTTP (`file://`, `gopher://`, `dict://`, `phar://`, `data://`, FTP, SMB, SMTP), so the protocol is received as a dedicated parameter and checked against an allowlist of `HTTP` or `HTTPS` only.
  Check: confirm the scheme is a fixed constant or validated against exactly HTTP/HTTPS, and that the HTTP library in use cannot be coerced into other schemes. Owner: `backend`. Source: SSRF Prevention.
- **Business data forwarded to an internal service without format validation.** Non-network strings sent along to the internal application are validated against the expected business or technical format: a regex for simple formats (token, zip code), string library functions for complex ones.
  Check: confirm each forwarded field has a bounded format check before it is placed into the outbound request. Owner: `backend`. Source: SSRF Prevention.

## Open-destination fetches (webhooks and arbitrary external URLs)

- **Arbitrary external destination not proven public.** When an allowlist is impossible, the application applies a blocklist: an IP must be public (not private, localhost, or IPv4/IPv6 link-local); a domain must be unknown to an internal-only DNS resolver, and every A and AAAA record must also pass the public-address check, with the connection bound to a validated address.
  Check: read the webhook or callback registration and dispatch code; confirm all resolved records are checked (not only the first), both address families are covered, and the dispatch connects to the checked IP. Owner: `backend`. Source: SSRF Prevention.
- **Deny-list missing the minimum published ranges.** Deny-lists are bypass-prone and allow-lists are preferred; when one is unavoidable it blocks at least `169.254.169.254`, `metadata.amazonaws.com`, `metadata.google.internal`, `127.0.0.0/8`, `0.0.0.0/8`, `::1/128`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`, `fe80::/10`, `224.0.0.0/4`, and `ff00::/8`.
  Check: compare the deny-list in code or config against this list; flag missing IPv6 ranges and metadata hostnames, and prefer a library predicate over string matching. Owner: `backend`. Source: SSRF Prevention.
- **No internal-domain registry or the internal resolver resolves external names.** Classifying a domain as internal requires the organization to maintain the list of internal domain names behind a centralized service; the internal DNS resolver queried for that check must not resolve external domain names.
  Check: confirm the internal-domain check queries a dedicated resolver and that its configuration has no forwarders to public DNS. Owner: `cloud`. Source: SSRF Prevention.
- **Outbound call to an external target lacks a proof of legitimacy.** The target application generates a random token (for example 20 alphanumeric characters) that the caller passes in the body of an HTTP POST under a parameter name restricted to `[a-z]{1,10}`, with the token itself restricted to `[a-zA-Z0-9]{20}`; the receiving endpoint accepts only POST, and the request is built only from validated information.
  Check: confirm the parameter name and token inputs are validated with those exact character sets and that the dispatcher sends POST with no unvalidated fields. Owner: `backend`. Source: SSRF Prevention.

## Network and cloud controls

- **Application host has unrestricted egress.** A firewall (device or OS-level) limits the application to the routes it legitimately needs, and network segregation is highly recommended so illegitimate calls are blocked at the network level even if application validation fails.
  Check: read security groups, network policies, or egress rules for the workload; flag `0.0.0.0/0` egress or access to internal subnets the feature does not need. Owner: `cloud`. Source: SSRF Prevention.
- **IMDSv1 still enabled on AWS compute.** Metadata services are the classic SSRF credential target; migrate to IMDSv2 and disable IMDSv1.
  Check: in IaC, confirm every instance and launch template sets the metadata options to require session tokens (IMDSv2 only). Owner: `cloud`. Source: SSRF Prevention.
- **Organization domains resolved by external resolvers first.** Domains belonging to the organization are resolved by the internal DNS server first in the resolver chain; this is detection support, not a substitute for connection-time enforcement.
  Check: read resolver configuration for the workload (VPC DNS, `resolv.conf`, cluster DNS) and confirm internal zones are served internally first. Owner: `cloud`. Source: SSRF Prevention.
- **Allowlisted domains not monitored for internal resolution.** A scheduled check alerts when an allowlisted domain resolves to a local IPv4/IPv6 address, or when a domain outside the organization resolves to an internal (private-range) address.
  Check: confirm a monitoring job or alert rule exists that resolves each allowlisted domain (A and AAAA) and fails on non-global addresses. Owner: `sre`. Source: SSRF Prevention.

## Related

- See `xml-and-deserialization.md` for XXE, which is an SSRF vector when XML parsers resolve external entities.
