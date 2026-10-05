# Consent and privacy

When to read: the brief or diff touches Consent Mode signals, consent gating, regional rules, redaction, url passthrough, or any tag that reads or writes personal data.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Tag fires before consent.** A marketing or analytics tag that stores or transmits personal data fires before the consent signal is known, or ignores a denied state, collecting with no lawful basis.
  Check: every tag that stores or transmits personal data is gated on the relevant consent signal; the default state is denied for EEA traffic until the CMP updates it.
- **Consent Mode signals incomplete.** Google tags need `ad_storage`, `analytics_storage`, and the v2 pair `ad_user_data` and `ad_personalization`; missing the v2 pair degrades or disqualifies remarketing and modeling.
  Check: all four Consent Mode v2 signals are set from the CMP, with a default command before the container and an update on the user's choice.
- **Consent values not the expected strings.** States passed as booleans (`false`) instead of the strings `'granted'` or `'denied'` are unrecognized, so the tag behaves as if consent were unset.
  Check: every consent value is the string `'granted'` or `'denied'`, in both the default and the update command.
- **Default runs too late.** A consent default that runs after tags have already evaluated lets them fire in the unknown state.
  Check: the default consent command runs before any Google tag loads (a consent-init tag sequenced first, or set in the page head before the snippet).
- **Redaction and passthrough backwards.** With `ad_storage` denied, ad-click identifiers should be redacted and `url_passthrough` should carry gclid/wbraid so conversions still model without cookies; getting these wrong leaks identifiers or loses all modeling.
  Check: `ads_data_redaction` is true when `ad_storage` is denied; `url_passthrough` is enabled where the ad platforms support it.
- **Non-Google tags ungated.** Meta, TikTok, and other third-party tags have no built-in consent checks, so they fire regardless of the Consent Mode signal unless the container gates them explicitly.
  Check: each non-Google tag carries an explicit consent condition (an additional-consent gate or a blocking trigger), not just the Google Consent Mode signals.
- **Server-side ignores consent.** Moving a tag to the server does not move the lawful basis; a server tag forwarding data for a denied purpose is the same violation, harder to see.
  Check: the consent state travels to the server in the event payload and gates server-side tags exactly as it gates client-side ones.
- **Region logic wrong or absent.** Consent applied globally (needlessly blocking non-EEA) or not at all (collecting in the EEA without consent), or region derived from an unreliable signal.
  Check: regional behavior matches the legal requirement per market, driven by the CMP's geolocation, not guessed from language or timezone.
- **Purpose overreach.** Consent for one purpose is used to send data to a destination for a different purpose, exceeding the basis.
  Check: each destination receives only the data its consented purpose covers; sensitive categories (health, financial) destinations now reject are never sent; purpose limitation holds across tags.
- **Consent path untested.** No way to prove which tags fired for a given state, so QA only ever exercises the granted path.
  Check: both granted and denied states are exercised in Preview and Tag Assistant; the denied path shows the expected tags blocked or cookieless.

## Escalation triggers (`needs-decision`)

- Any change that would let a tag collect or forward personal data in a denied or unknown consent state: a hard stop, escalate rather than ship it.
- A new destination for personal data, or a new purpose for data already collected (a lawful-basis decision, not an implementation detail; also an ask-first boundary in the agent).

## What good looks like

- Default-denied for EEA, all four Consent Mode v2 signals wired from the CMP, defaults before the container.
- The same consent state gates client and server tags; denied means blocked or cookieless, verifiably.
- Redaction and passthrough set so consented modeling survives without storing identifiers unlawfully.
