# Desktop security

When to read: the brief or diff touches remote content or navigation, custom protocol and URL handlers, entitlements, sandbox or hardened-runtime settings, a local listening port, bundled credentials, or the signing and notarization path.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Remote content behind a privileged bridge.** A window that can reach a remote origin and also holds a bridge to the privileged side gives that origin the bridge, and one injected script becomes local code execution.
  Check: windows holding any privileged surface load local content only; remote content lives in a window with no bridge, or the bridge is removed.
- **Navigation and window opening allowed by default.** A link, a redirect, or a script-opened window quietly moves a trusted window to an untrusted origin while keeping everything that window was granted.
  Check: navigation is denied by default and allowlisted by origin; external links open in the system browser rather than in an app window.
- **Custom protocol handler as an unauthenticated entry point.** The OS routes a scheme from any web page or any other app straight into your handler, so parsing that URL into an action is a remotely triggered command channel. On some platforms the whole URI arrives as a command-line argument, so a crafted URL injects runtime switches into a process that has not started yet, which is a distinct and older bug than a bad route parameter.
  Check: the registration terminates its argument list so a URL cannot be read as a switch, arriving arguments that look like flags are rejected, and URL parameters never select a filesystem path, a command, or an account; anything state-changing re-checks authorization.
- **Build-time hardening left at defaults.** Several of the toggles that matter most (Electron calls them fuses) are flipped at package time and baked into the shipped binary rather than being settable at runtime, and the permissive ones ship enabled: the ability to re-run the app binary as a plain script runtime, to inject runtime options through the environment, and to attach a debugger. The protective ones, archive integrity validation and refusing to load app code from anywhere but that archive, ship disabled and are only meaningful together.
  Check: the packaging configuration is part of the diff review, the living-off-the-land toggles are off, and integrity validation is on alongside the flag that stops code loading from outside the verified archive.
- **A local listener reachable from the browser.** A debug port, an IPC-over-HTTP server, or a websocket with no origin check is callable by any page the user has open even when bound to loopback, since a page can simply fetch the local address and a host check falls to DNS rebinding; binding beyond loopback extends that audience to the whole network.
  Check: local listeners bind to loopback, require a per-run secret, and verify the request origin; debug surfaces are absent from packaged builds.
- **Entitlement widened to make a dependency load.** Disabling library validation lets a dylib signed by anyone load into the process; allowing unsigned executable memory or environment-controlled dynamic linking removes protections just as broadly. Each is added once to silence a build error and never removed.
  Check: an entitlement added in the diff names the specific dependency that requires it and records that the narrower options (re-signing the dependency, a scoped just-in-time exception) were ruled out first; the same applies to a temporary sandbox exception standing in for a user-selected file grant.
- **Signing state assumed from a green build.** Two different failures get conflated: a build that is not notarized is refused wherever the quarantine flag is set, online or offline, because the answer comes back negative rather than unavailable; a build that is notarized but never stapled works only while the machine can reach the notary service, which is exactly the dependency stapling removes. Adding a native module, a bundled executable, a framework, or a helper service also changes what must be signed inside-out, and that breaks at release time weeks after the commit.
  Check: adding a bundled binary updates the signing manifest, entitlements, and notarize-then-staple ordering in the same change, and the locally produced signed build is verified with the platform's own verification tooling rather than inferred from the build exiting zero; verifying the notarized artifact itself is the shipping human's step, named in the report's Ship path.
- **Credentials in the bundle.** An API key, a token, or a private endpoint compiled into the app or its packed resources is recovered by unzipping the artifact.
  Check: nothing in source, config, or bundled resources is a credential; anything the client must hold is scoped as if it were public, because it is.
- **A document format that can execute.** Opening a user- or network-supplied file into a parser that can construct objects, expand templates, or evaluate expressions turns "open file" into code execution.
  Check: parsers applied to untrusted documents are data-only, with bounds on size and nesting.
- **Dependency added without identity confirmation.** Lookalike and hallucinated package names are a live supply-chain attack, and a desktop app ships its dependencies to the user's machine with the app's own privileges.
  Check: every added dependency resolves to the real, maintained project, and its addition is escalated rather than assumed.

## Escalation triggers (`needs-decision`)

- Adding or widening an entitlement, capability, or scoped sandbox exception the feature legitimately requires (also an ask-first boundary in the agent, so the caller may approve it).
- Disabling library validation or allowing unsigned executable memory: this escalates and stays refused, since the agent's never tier holds it rather than its ask-first tier.
- Loading remote content in a window that holds a privileged bridge, or registering a new custom protocol scheme.

## What good looks like

- Nothing arriving from outside the process is trusted: not a URL, not a document, not an update payload, not a dependency name.
- Signing, notarization, and stapling are verified against the artifact a user would download.
- Every entitlement can be traced to the feature that needs it, and the list only ever shrinks by accident.
