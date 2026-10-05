# Tags, triggers, and variables

When to read: the brief or diff touches triggers and exceptions, tag firing or sequencing, variables and their defaults, or container naming and structure.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Trigger over-fires.** An all-pages or too-broad trigger fires a tag where it must not (a purchase tag on every pageview, a remarketing tag site-wide), inflating counts and ad spend.
  Check: the trigger is scoped to the exact condition (event name, page path, click target); "All Pages" is a justified choice, not the default.
- **Trigger under-fires or races.** A data-dependent tag bound to a page-load trigger fires before the push that carries its data; a DOM trigger binds to an element rendered later.
  Check: data-dependent tags fire on the event that carries the data; element triggers account for async rendering.
- **Missing exception or blocking trigger.** A tag has no exception for states where it must not fire (consent denied, internal or QA traffic, non-production hostnames), so it fires everywhere.
  Check: exceptions cover consent-denied and internal/QA traffic, and staging hosts where applicable.
- **Ordering left to luck.** A tag depends on another running first (consent init before measurement, a library before its calls) but ordering rests on trigger timing.
  Check: hard ordering uses tag sequencing (setup/cleanup tags) or a gating trigger, not coincidence.
- **Double firing.** The same pageview or conversion fires from two tags (a migrated tag left enabled beside its replacement, or gtag alongside a GTM tag), double-counting.
  Check: exactly one tag owns each event; retired tags are paused or removed, not left running in parallel.
- **Default masks a failure.** A variable returns a default when its source is missing, so tags fire with placeholder data instead of failing loudly.
  Check: defaults are used only where a blank is genuinely valid; missing required inputs block the tag.
- **Built-in variable off.** Reading `Click URL` or `Form ID` without enabling the built-in variable, or relying on auto-event data that is disabled, yields `undefined`.
  Check: required built-in variables are enabled; auto-event data is confirmed present in Preview.
- **Container hygiene rot.** Unnamed, unfoldered, or copy-pasted tags make what-fires-when unknowable; a workspace edits stale against a newer published version.
  Check: consistent naming and folders; the workspace is synced to the latest container version before editing.

## Escalation triggers (`needs-decision`)

- Deleting tags, triggers, or templates outside your scope, or removing ones other stakeholders rely on (also an ask-first boundary in the agent).
- Publishing a container version (a human publishes; see measurement-integrity-and-release).

## What good looks like

- Each event has exactly one owning tag on a precisely scoped trigger with the right exceptions.
- Ordering that matters is enforced by sequencing, not trigger timing.
- Names, folders, and versions are legible enough that a stranger can tell what fires when.
