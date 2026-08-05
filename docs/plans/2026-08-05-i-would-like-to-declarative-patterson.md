# `hostof`: a deployment fingerprinting CLI

## Context

There is no way here to answer "where is this site actually deployed" without opening a browser and reading response headers by hand.
The ask is a script that takes a URL and reports which hosting service and region serve the frontend and the backend, from public data plus ordinary browser-like requests, going deeper than whois.

Scope settled at intake:

| Decision | Answer |
|---|---|
| Targets | Third-party sites, not controlled by us |
| Default depth | Passive datasets plus browser-normal requests only |
| Deeper probing | Conventional undocumented paths behind `--deep`, gated by an authorization file |
| Precision promised | Vendor plus region. Project and account ids are best-effort, never promised |
| Name | `hostof` (`whereis` collides with `/usr/bin/whereis`) |
| Role | `coreutils` |
| Vendor detection | Hand-maintained rule table, no vendored corpus |

Because the targets are third parties, the passive/active line is the design's central constraint rather than a footnote.

## Feasibility: verified, with a stated ceiling

**Vendor plus region is reliably achievable.** Verified live during research:

- `curl -sS -o /dev/null -D - https://vercel.com/` returns `server: Vercel` and `x-vercel-id: fra1::iad1::7dqhk-...`, giving edge region and compute region from one request.
- `https://www.netlify.com/` returns `server: Netlify`, `x-nf-request-id`, and `server-timing: dc;desc="aws-fra"`, where that last header is the best Netlify region tell because it names the underlying AWS region.
- `https://ip-ranges.amazonaws.com/ip-ranges.json` fetches keyless and carries `{"ip_prefix":..., "region":"eu-west-1", "service":"AMAZON"}` per prefix. `https://www.gstatic.com/ipranges/cloud.json` carries `scope` (the region), though its `service` is always the literal `"Google Cloud"`.

**Project and account ids are a coin flip, and that is why they are not the promise.** Bounded crawls of linear.app, openai.com, stripe.com, docker.com, slack.com, supabase.com and nuxt.com returned **zero** project identifiers. Vercel's own `.map` files return HTTP 403 behind Protected Source Maps. Realistic hit rate on a serious production app is **30 to 50%**, driven by whether source maps shipped and whether a Firebase or Supabase config is present.

**AWS account ID is not passively obtainable at all.** The `s3:ResourceAccount` technique needs the caller's own authenticated AWS role, so it is out of scope by construction.

This yields a hard output requirement: **project id is nullable and absence reports "not exposed" rather than "not found"**, because those render identically and mean opposite things.

## Legal constraints

Engineering research, not legal advice; anything client-facing needs Didomi's counsel first.

Everything turns on one question: is the target's machine touched, and if so, is it touched the way a browser touches it?

| Cat | Behaviour | Status |
|---|---|---|
| (a) | Third-party datasets: RDAP, CT logs, passive DNS, published cloud IP ranges | Lawful. Target never contacted |
| (b) | Browser-equivalent requests: `GET /`, following links, fetching linked JS, TLS handshake | Lawful in both US and EU |
| (c) | Undocumented-but-conventional paths: `/openapi.json`, `/health` | Genuine grey zone, splits by jurisdiction |
| (d) | Port scans, malformed requests, bucket enumeration, credential attempts | Do not build |

The authorities that make (b) safe:

- **Van Buren v. United States**, 593 U.S. 374 (2021) reduced CFAA "exceeds authorized access" to a "gates-up-or-down inquiry", rejecting a reading that would criminalise "a breathtaking amount of commonplace computer activity". Footnote 8 leaves open whether the gate is technological or contractual, so ToS-only theories are wounded rather than dead.
- **hiQ Labs v. LinkedIn**, 31 F.4th 1180 (9th Cir. 2022): where a network generally permits public access, accessing that public data is likely not access "without authorization".
- **Directive 2013/40/EU** Recital 17 is the EU equivalent: a ToS breach "should not incur criminal liability" as the sole basis.

Category (c) is where jurisdictions split, and this is the finding that shapes the design:

- **Spain, CP art. 197 bis.1** makes security-measure circumvention (`vulnerando las medidas de seguridad establecidas para impedirlo`) an *element of the offence*. Unauthenticated content served to any requester has no measure to breach, so (a), (b) and most of (c) fall outside it on the statutory text.
- **France, CP art. 323-1** has **no circumvention element**. *Kitetoa* (CA Paris, 2002) acquitted ordinary-browser access to an unsecured site, but *Bluetouff* (Cass. crim., 20 May 2015, n° 14-81.336) convicted for *maintien frauduleux* where the defendant knew the resource was meant to be protected. The discriminator is **demonstrated awareness that the resource was not meant to be public**, which is exactly what a `/.git/config` fetch evidences.

So `--deep` cannot be a plain flag. It is gated on an authorization file recording a basis per host, and refuses any host not listed. For a third party with no relationship that makes `--deep` unusable by design, which is the correct outcome. Research also found that nearly every useful signal is category (b) anyway, so `--deep` adds little: it ships because it was asked for, not because it carries the value.

Three constraints that bite harder than criminal law:

- **GDPR.** Results become personal data via RDAP registrant fields, a developer name or `/Users/<name>/` path in a source map, or a git author. Storing them makes us a controller needing an art. 6(1)(f) LIA, retention limits and art. 14 notice within a month. Redact at ingest and never persist a personal field.
- **Database right** (Dir. 96/9/EC art. 7(1), 7(5)): per-target CT and RDAP queries are fine, but mirroring a vendor's fingerprint DB or bulk-harvesting WHOIS is substantial-part extraction.
- **Provider terms**, the likeliest real constraint. `ip-api.com` is non-commercial only ("strictly limited for a non-commercial purpose and in a non-commercial environment") and Cloudflare Radar is CC BY-NC 4.0, so both are disqualified for work use. urlscan.io requires written permission for any commercial use *and* publishes non-private scans, so it is out twice over. Shodan and Censys do permit commercial use, Shodan requiring attribution and forbidding resale. GeoLite2 stopped being CC BY-SA in 2019 and now carries a proprietary EULA with a key requirement and a 30-day deletion obligation, so it is not shipped.

`robots.txt` is a convention, not a statute. Its one legal edge is DSM art. 4(3) as the machine-readable TDM reservation. Treat it as policy we adopt, because ignoring it generates the cease-and-desist that would move us from green to red under the *Power Ventures* line.

### Guardrails the tool must implement

1. Category (b) is both the default and the ceiling. Nothing path-guessed without the flag.
2. Rate limit **per host**: at most 1 req/s, at most 10 requests per target, a hard cap, and absolute respect for `429`/`503`/`Retry-After`. This keeps us clear of CP art. 264 and trespass to chattels.
3. Honest `User-Agent` with a contact URL. Never impersonate a browser, never rotate UA or egress IP. A blocked request is a final answer.
4. Fetch and obey `robots.txt` as policy.
5. `--deep` requires an authorization entry (host, basis, expiry) and logs the basis into the output.
6. A refusal list that is **absent from the code rather than flag-gated**: `/.git/*`, `/.env*`, backup extensions, `/server-status`, admin and credential-shaped paths. Gate on the specific path, never the prefix, because `/actuator/health` is (c) while `/actuator/env` dumps config and is (d).
7. No credential attempts, no WAF or CAPTCHA solving, no `Host` rewriting, no TLS verification bypass. Stop on 401/403 and record it as the finding.
8. Redact personal data at ingest via a field allowlist (registrar, nameservers, dates, ASN, org).
9. Never submit the target URL to a third-party scanner.
10. No `-jarm`-style probing if `httpx` is ever added later: it sends 10 crafted TLS Client Hellos, which is not browser-normal.

## Design

### The pipeline, and the one rule that matters most

Research surfaced what looked like an ordering problem and the adversarial pass showed it is really a **merging** problem. `docs.netlify.com`, `www.netlify.com`, `www.smashingmagazine.com` and `www.gatsbyjs.com` all resolve to the identical pair `15.197.167.90` / `3.33.186.135`, which RIPEstat attributes to **AS16509 Amazon**, with whois NetName `AT-88-Z` and IRR description "Amazon GlobalAccelerator Prefix". Netlify appears nowhere in registry data.

I confirmed the service directly against AWS's own file: both addresses fall in `15.197.128.0/17` and `3.33.128.0/17`, service `GLOBALACCELERATOR`, region `GLOBAL`.

The tempting conclusion (ASN is wrong, so fingerprint first) is itself wrong. **Netlify genuinely does run on AWS Global Accelerator, so AS16509 is correct at the network layer.** It is not a misattribution. The defect is collapsing two true facts into one verdict.

So the rule is: **emit `edge` and `network` as separate, never-merged fields.** `edge: Netlify` and `network: AS16509 Amazon` are both right, and a tool that prints one of them as "the answer" is lying whichever it picks. Vercel makes the point sharper: `76.76.21.0/24` whois is `Vercel, Inc (ZEITI)`, NetName `VERCEL-01`, while its IRR origin is AS16509 as BYOIP space, and it is absent from `ip-ranges.json` entirely (I verified the `NO MATCH`). Registry says Vercel, routing says Amazon. An ASN-first design and a registry-first design pick different wrong answers; reporting both layers is the only honest output.

The pipeline:

1. **Normalise** the input, accepting a URL or a bare host.
2. **DNS.** CNAME chain (highest-yield single signal), A/AAAA, NS, TXT. `dig` primary since macOS ships `/usr/bin/dig`, with a `--doh` fallback over HTTPS for networks blocking UDP/53.
3. **HTTP.** One request, then read **every** vendor header rather than stopping at the first match. This is load-bearing: `linear.app` returns `server: cloudflare` **and** `via: 1.1 google` on the same response, so one request names both edge and origin vendor.
4. **Origin split.** Extract `<link rel=preconnect|dns-prefetch>` and asset origins from the HTML, then re-fingerprint each distinct origin. `preconnect` is the strongest signal because an author only preconnects to origins the page actually calls.
5. **Bounded chunk crawl** for the best-effort tier only.
6. **IP attribution last**, as a separate reported layer: match the resolved IP against cached provider prefix files for vendor plus region, falling back to RIPEstat for ASN.

### When an IP-derived region is meaningful, and when it is not

This is the sharpest limit in the design, and I measured it rather than assuming it. Counting AWS's 10,619 published prefixes:

| Service | Prefixes | `region: GLOBAL` (unusable) |
|---|---|---|
| All AWS | 10,619 | 484 (4%) |
| `API_GATEWAY` | 214 | 0 (0%) |
| `EC2` | 1,902 | 21 (1%) |
| `ROUTE53` | n/a | 31% |
| `GLOBALACCELERATOR` | 131 | 45 (34%) |
| `CLOUDFRONT` | 211 | 118 (55%) |
| `CLOUDFRONT_ORIGIN_FACING` | 45 | 43 (96%) |
| All GCP | 1,091 | 44 (4%) |

The aggregate 4% looks reassuring and is misleading. The services a client-observed IP actually resolves to for a CDN-fronted site are exactly the two worst rows: over half of CloudFront prefixes and a third of Global Accelerator prefixes carry `GLOBAL`, which answers nothing. Meanwhile a bare origin IP on EC2 or API Gateway carries a real region essentially always.

So **an IP-derived region is trustworthy for an origin and near-worthless for an edge**, and the tool must know which it is looking at before it reports one. For an anycast edge, region comes from the response header (`x-vercel-id` compute region, `server-timing: dc;desc="aws-fra"`) or is reported absent. Printing `GLOBAL` as a region, or silently dropping it and showing the vendor alone, are both worse than saying "edge, region not determinable".

The failure mode is better than feared: for a CDN-fronted site the IP layer does not report a *wrong* region, it reports **none**, because either the prefix says `GLOBAL` or the address is absent from both files entirely (Cloudflare, Fastly and Vercel anycast are in neither). It fails visibly. The consequence is that the IP layer is a bare-origin tool rather than a general one, which is why the headers are the primary path.

Two corrections from the adversarial pass, both kept in the implementation:

- **Longest-prefix match is mandatory, not an optimisation.** A first-match-wins matcher returns the `AMAZON` supernet's region instead of the specific service's, since one address legitimately matches both at the same prefix length in AWS's own file.
- **This prefix-matching layer is not novel and is not described as such.** `nccgroup/cloud_ip_ranges` is 156 lines of Python reading the same two URLs and printing the same `region` and `scope` fields, and `digaws`, `py-cloudip` and `cloudiplookup` overlap too. It is written here anyway because the repo's tools are stdlib-only at runtime and a dependency is the thing being avoided, not because the wheel was missing. `cdncheck` genuinely cannot substitute: it regexes CIDRs out of those files rather than parsing them (`generate/input.go:186`) into a `map[string][]string` with nowhere to put a region, so the field is destroyed at ingest.

One fact that arrived late and strengthens the header-first design: Vercel documents `x-vercel-id` as carrying the region the function **executed in** rather than merely the POPs traversed, so the compute region answers the deployment question directly instead of by inference.

### CNAME suffixes are the durable fingerprint; hardcoded IPs are not

The adversarial pass killed the hardcoded-IP-table idea on a ground I had not considered. The table is **already incomplete**: apex-configured Netlify sites use a different, disjoint pair (`apex-loadbalancer.netlify.com` gives `75.2.60.5` + `99.83.231.61`), so a rule built on the first pair misses them entirely. And AWS returns a released Global Accelerator static IP to the general pool after 10 days and reuses it, so a stale entry ages into pointing at an unrelated AWS customer. That failure mode is **silent misattribution rather than a clean miss**, which is the one the repo's own `port.fish` precedent says to avoid.

The stable signal is the CNAME suffix, because the vendor controls it: `netlifyglobalcdn.com`, `cname.vercel-dns.com`, `edgekey.net`, `map.fastly.net`, `shops.myshopify.com`. Those are the fingerprints to encode. Hardcoded IPs drop to **corroboration only, with a visible staleness date in the output**, never a primary verdict.

One caution the same pass raised, which no fingerprint can fix: a Cloudflare-proxied site shows Cloudflare IPs and headers whatever the origin runs, so for those the origin is genuinely masked and the tool must say so rather than report the edge as the answer.

### Region extraction rules worth pinning now

The `x-vercel-id` parse is the one place a naive rule breaks, and research verified three distinct shapes:

| Shape | Observed | Reading |
|---|---|---|
| 3-field | `fra1::iad1::7dqhk-...` | edge `fra1`, compute `iad1` |
| 2-field | `fra1::2cshq-...` | edge only, no distinct compute region |
| multi-hop | `fra1:fra1:sfo1:...:sfo1::sfo1::j5mk6-...` | routing chain, then compute region |

So the rule is: **split on `::`, take the last segment before the request-id segment as the compute region, and treat a two-segment value as having no compute region.** Reading "the second field" literally returns a request id on the two-field form.

Other region-bearing signals: `server-timing: dc;desc="aws-fra"` (Netlify), `x-amz-cf-pop` (CloudFront POP), `cf-ray` IATA suffix, `fly-request-id` `-fra` suffix, `x-github-edge-region`, `x-azure-ref` POP, Fastly `x-served-by` (one POP per chain element), and hostname-encoded regions in `<name>-<id>.<region>.elb.amazonaws.com`, `<api-id>.execute-api.<region>.amazonaws.com`, and `<service>-<project-number>.<region>.run.app`.

Vercel, Netlify, Cloudflare, Fastly, Akamai, Shopify, Webflow, Heroku, Render and Fly custom domains encode **no** region in the hostname, so for those the header is the only path.

### Why a hand-maintained table rather than a corpus

Every live Wappalyzer-descended dataset is **GPL-3.0**, including the data behind the MIT-labelled `wappalyzergo` (its `LICENSE.md` covers the Go port; its README states the data comes from `HTTPArchive/wappalyzer`, which is GPL-3.0). Vendoring that JSON into a distributed script would relicense the script.

That question is moot here, because **no existing dataset extracts region or POP at all**. Every ruleset maps headers to vendor names only. The region layer is original work regardless of corpus, it is roughly 25 rules, and keeping it hand-written preserves the repo's stdlib-only runtime rule.

### Bounding the chunk crawl

An unbounded crawl timed out at 120s during research, and posthog.com's 8 chunks alone were 10 MB. The budget:

- `--max-filesize 3000000` and `--max-time 8` per chunk, `--max-time 10` on the entry document
- 5 to 10 chunks, since config lives in eagerly-loaded entry and vendor chunks rather than lazy route chunks
- regex the stream, never buffer to memory
- overall per-target deadline around 30s

**`grep -a` is required.** Minified bundles trip binary detection and `grep` then silently prints nothing, which presents as "this site exposes nothing".

## Files

### New: `roles/coreutils/files/scripts/hostof/`

```
hostof                                        executable, +x, single python file
dotkit -> ../../../../../lib/python/dotkit    committed relative symlink
tests/test_hostof.py
```

Template is **`roles/work/files/scripts/weekly-recap/weekly-recap`**, a single 14 KB executable file, not the `claude-kit` package (which is a package only because pytest needs to import something that large). Copy its shape:

- `sys.path.insert(0, str(Path(__file__).resolve().parent))` then `from dotkit import ui`, per `weekly-recap:22-24`
- module-level `EXIT_OK = 0` / `EXIT_USAGE = 1`, extended here with `EXIT_UNREACHABLE` and `EXIT_REFUSED` for the `--deep` gate
- the `Parser(argparse.ArgumentParser)` subclass overriding `error()` at `weekly-recap:357-362`, which is load-bearing: without it argparse exits 2, a code the tool's vocabulary does not define
- `main(argv=None)` returning an int, and `sys.exit(main())`

Output goes through `dotkit.ui` with no hand-rolled escapes: `title`/`step`/`ok`/`warn`/`err`/`item`/`note`/`done`, plus `ui.paint` for coloured row fragments and `ui.path` for `$HOME` collapsing. Only `title` and `note` paint their text; elsewhere the glyph carries the colour. Emoji only on a `title` or `done`.

Follow `port.fish`'s two habits, since it is the closest existing neighbour: a shape the tool cannot model yields **nothing** rather than a fabricated value, and only the security-relevant field is non-dim while everything else is dim.

`--json` follows `listing.py`: `print(json.dumps(...))` of the rows verbatim, with human asides redirected to stderr because stdout is a payload.

The authorization file is **JSON, not YAML**, because the runtime is stdlib-only and PyYAML is a test-only dependency here.

Prefix-file caching goes under `~/.cache/hostof/` with a TTL; the AWS file alone is 2.5 MB, so it is not fetched per run.

### Modified

| File | Change |
|---|---|
| `roles/coreutils/defaults/main.yml` | Add a `CORE_SCRIPTS` manifest with `- hostof` |
| `roles/coreutils/tasks/main.yml` | Add the link task, copying `roles/ai/tasks/main.yml:114-129`. **`src` must keep `{{ role_path }}`**: `ansible.builtin.file` does not resolve `src` through the role search path, and `force: true` skips the existence check, so a relative `src` writes a dangling link and still reports `changed`. Also add `{{ HOME }}/.local/bin` to a directory-ensure task, because `coreutils` runs at position 21 in `dotfiles.yml` while `~/.local/bin` is created by `ai` at position 36 |
| `pytest.ini` | Add `roles/coreutils/files/scripts/hostof/tests` to `testpaths` |
| `roles/ai/files/scripts/claude-kit/tests/test_packaging.py:27-28` | Add a third tuple `("coreutils", "CORE_SCRIPTS", "Link core scripts into the user bin directory")` to the `ROLES` list, so the new role's manifest and task shape are checked like the other two |
| `roles/coreutils/README.md` | Name the tool, matching how `roles/ai/README.md:10` and `roles/work/README.md:9,16` do |

No new brew packages. `dig` is `/usr/bin/dig` (OS-provided) and `curl` is system; `openssl` is already present via brew.

### Test constraints that will fail CI if missed

From `lib/python/tests/test_suites.py`:

- `:86` every discovered suite directory must appear in `pytest.ini` `testpaths`, so the new suite fails CI until its line is added
- `:123` suite module basenames are globally unique, hence `test_hostof.py`
- `:102` nothing may `import conftest`; shared paths come from `dotkit.testing`
- `:185`/`:208` the `dotkit` link must be relative and resolve to `lib/python/dotkit`
- no suite directory may hold `__init__.py`

Follow `weekly-recap`'s test style: no conftest, one module, drive the tool as a subprocess with external CLIs replaced by generated stub scripts on a narrowed `PATH`, and have the stub **exit 97 on no match** so a forgotten rule fails loudly rather than reading as an empty result. Its shebang points at `sys.executable` deliberately, since `/usr/bin/python3` is the Command Line Tools shim and costs about 1.4s per call.

## Verification

Network access is uneven inside Claude Code, so verification splits three ways.

**Unit, runs in `make test`.** Parsing is pure and carries the subtle logic, so it gets the coverage: the three `x-vercel-id` shapes, `server-timing` region extraction, POP-code mapping, CIDR prefix matching against fixture slices of the provider files, the `::`-split rule, and the `--deep` refusal when a host is absent from the authorization file. Stub every network call.

**Reachable from Claude Code.** `ip-ranges.amazonaws.com` and `cloudflare.com/ips-v4` fetch from Bash. DNS-over-HTTPS (`dns.google/resolve`) and `crt.sh?output=json` are blocked in Bash but **do work through WebFetch**, which egresses server-side, so the DNS and CT layers can be partially exercised in-session.

**Requires the user's own shell via the `!` prefix.** Anything needing a raw socket or the real client IP: `dig`, `openssl s_client`, `whois`, and any header check where the observed `remote_ip` matters, since the Bash proxy reports `127.0.0.1` for every HTTPS call.

Acceptance runs, in the user's shell:

```
! hostof vercel.com          # expect Vercel, edge fra1, compute iad1
! hostof www.netlify.com     # expect Netlify, region aws-fra from server-timing
! hostof linear.app          # expect BOTH cloudflare edge and google origin, not one
! hostof docs.netlify.com    # expect Netlify, NOT "AWS" despite AS16509
! hostof --json vercel.com | jq .
! hostof --deep example.com  # expect EXIT_REFUSED, host not authorized
```

That fourth case is the regression test for the attribution trap and the fifth for the ordering rule, so both belong in the acceptance set rather than only in unit tests.

Then `make test` and `make check-role ROLE=coreutils` for the Ansible half.

## Risks and open questions

- **`crt.sh` is unreliable by nature**, returning HTTP 502 on roughly one call in three during research, and its rate limit is 5 requests/minute/IP. Treat CT as best-effort with backoff. Cert Spotter's free tier returned 403 unauthenticated and is not a usable fallback.
- **Azure has no stable JSON IP-range URL.** It is a weekly download behind an HTML page, and the Service Tag Discovery API needs an authenticated subscription. Azure region attribution is therefore out of scope for v1 rather than half-built.
- **`--deep` will be unusable on the intended targets.** It is built as specified and gated as specified, but for third parties with no relationship the gate refuses by design.
- **A Cloudflare-proxied origin is genuinely undiscoverable**, and so are server-side env vars, the cloud account, the deploy pipeline and the org behind a custom domain. The tool must report these as masked rather than reporting the edge as the answer.
- **GCP's global share is now measured** and matches AWS closely: 44 of 1,091 prefixes (4%) carry `scope: global`, across 48 distinct scopes. The edge-versus-origin caveat still applies.

## What the adversarial pass changed

The refutation round changed the design rather than confirming it, which is worth recording so the reasoning is not re-litigated later.

| Claim | Challenge | Outcome |
|---|---|---|
| The shared Netlify IP pair should be treated as a Netlify fingerprint | Those are AWS Global Accelerator addresses, so any AWS customer could have them, making the rule a false-positive generator | **Partially refuted, and my own planned fix was wrong.** Global Accelerator assigns two *dedicated* IPs per accelerator rather than drawing from a shared pool, and `netlify.netlifyglobalcdn.com` resolves to exactly that pair, so it really is Netlify-specific. The table dies for a different reason: it is already incomplete (apex sites use a disjoint pair) and released GA IPs are reused after 10 days, so it rots into silent misattribution |
| Vendor fingerprints must be evaluated before ASN attribution | This treats two true facts as rivals | **Refuted as framed.** Netlify does run on AWS Global Accelerator, so AS16509 is correct at the network layer. The defect was collapsing, not ordering, so the design now emits `edge` and `network` as never-merged fields |
| Provider IP-range files answer region | A client-observed IP is usually an anycast edge, so the matched prefix describes the edge rather than the deployment | **Holds, but heavily qualified by measurement.** 55% of CloudFront prefixes and 34% of Global Accelerator prefixes carry `region: GLOBAL`, against 1% for EC2 and 0% for API Gateway. Region from IP is trustworthy for an origin and near-worthless for an edge |
| `x-vercel-id` field 2 is the origin region | Three value shapes exist in the wild | **Corrected.** The two-field form has no compute region and the multi-hop form puts a routing hop where field 2 would be, so the rule is a `::` split taking the last segment before the request id |
| GeoLite2 is CC BY-SA with an attribution requirement | It changed licence in 2019 | **Corrected.** Proprietary EULA, licence key required, 30-day deletion obligation. Not shipped; RIPEstat used instead |
| Shodan, Censys and BuiltWith free tiers forbid commercial use | Read the actual terms | **Corrected, and inverted.** Shodan permits commercial use with attribution and forbids resale; Censys states no commercial restriction. The genuinely disqualified sources are `ip-api.com`, Cloudflare Radar and urlscan.io |
| DoH and `crt.sh` cannot be verified from inside Claude Code | Bash is not the only egress path | **Corrected.** Both work through WebFetch, which egresses server-side, so the DNS and CT layers move into the in-session test story |

| Provider IP-range files are the only region source, so this layer is necessary rather than reinvented | Read cdncheck's source and hunt for an existing IP-to-region tool | **Split.** The cdncheck half is confirmed at source level: it regexes CIDRs out of those exact two files into a type with nowhere to put a region. The novelty half is **refuted**: `nccgroup/cloud_ip_ranges` already does this in 156 lines. The layer is still written here because the runtime is stdlib-only, but the plan no longer claims it was missing |

## Implementation notes

Three defects surfaced after the plan was approved, two of them only by running the tool against real hosts, which is the argument for the live acceptance set over unit tests alone.

- **A truncated error body crashed the run.** A 404 whose body is a chunked response that ends early raises `http.client.IncompleteRead` from `exc.read()`. That is an `HTTPException` rather than an `OSError`, and because it is raised *inside* an `except` clause it escapes the whole `try` instead of reaching the broad handler below it, so `hostof docs.netlify.com` exited 1 with a traceback. This is the same trap `claude-kit`'s `upstream.py` documents. Both exception types are now listed, with a regression test that fakes the truncated read.
- **An unwritable cache directory crashed the run.** The provider prefix files are cached under `~/.cache/hostof`, and a sandbox or a read-only `HOME` makes that uncreatable. The cache is an optimisation, so it now degrades that source to nothing instead of ending an otherwise good report.
- **The Cloud Run region regex was wrong.** It bounded the region's first component to two letters, which matches `us-central1` but not `europe-west1` or `africa-south1`. Caught by a unit test before any live run.

### Presentation

The first working output was correct and hard to read, and fixing it surfaced a fourth defect.

- **Evidence was quoted whole.** A real `server-timing` carries a dozen metrics, so the edge row's proof line ran past 200 characters to convey `dc;desc="aws-fra"`. Only the matched fragment is quoted now, and everything else passes through a `brief()` bound so no evidence line can wrap and break the column it sits in.
- **`✓` and `⚠` were the wrong kinds.** `ok` means "it worked", but these are entries in a listing, so they are `item` rows and the difference between an answer and an absence is carried by colour, as `port.fish` does. Labels sit in a padded column, sized per section because the fixed labels are short while an identifier's kind is prose.
- **A didactic `note` fired on every run**, explaining that network is a separate fact from edge. That belongs in `--help`, not in each invocation.
- **The closing line graded the run** (`1 of 2 layers identified`) instead of answering. `summarise()` now states the finding: `Netlify (aws-fra), origin masked, 1 identifier exposed`.
- **The fourth defect: the umbrella service won a tie.** AWS lists `3.33.128.0/17` as both `AMAZON` and `GLOBALACCELERATOR`, at the *same* prefix length with `AMAZON` first, so longest-prefix match could not separate them and the report said `AMAZON`. That loses the one fact identifying the address as an anycast edge rather than an origin. The match now prefers the specific service on a tie, with tests for both that and for the umbrella still answering when it is the only match.

One further fix from the same pass: `tls_facts` called `socket.create_connection((host, 443))`, which re-resolves the hostname through `getaddrinfo` after DNS has already run. It now connects to the resolved address and passes the hostname as SNI, so verification still runs against the host, one redundant lookup disappears, and it works where the process cannot call `getaddrinfo` at all.

One deviation from the plan worth naming: the packaging test's list is called `INSTALLERS`, not `ROLES`, and `dotkit.testing` gained a `CORE_SCRIPTS_DIR` beside the two existing script-directory constants so the new suite locates the tool the same way the others do.
