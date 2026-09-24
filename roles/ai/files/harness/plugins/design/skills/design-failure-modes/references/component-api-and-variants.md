# Component API and variants

When to read: the brief or diff touches component props, variants, slots, composition, or shared and published component APIs.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Boolean prop proliferation.** Every added boolean doubles the state space; the flags interact, and most combinations are undesigned but shippable.
  Check: a new modifier joins an existing variant axis or becomes a composition slot; it does not land as a boolean beside other booleans it interacts with.
- **Breaking a consumed API for internal neatness.** Renamed props, removed variants, or changed exports break screens you cannot see from inside the component.
  Check: grep the consumers of every changed prop, variant, and export; changes are additive with a deprecation path, or escalated.
- **Default change wearing an additive coat.** Changing a default variant, size, or spacing silently restyles every existing call site that relied on the old default.
  Check: existing call sites render identically after the change, or the change is escalated as breaking.
- **Escape hatch without a contract.** Accepting arbitrary style or class overrides everywhere makes every internal detail public API; the next refactor breaks consumers who reached inside.
  Check: override points are deliberate and named (documented slots, parts, exposed tokens); internal structure and class names stay free to change.
- **One-off built beside the system.** A near-duplicate of an existing component forks maintenance; the two drift until neither matches the design.
  Check: the diff extends the existing component with a variant or slot, or the report justifies why it cannot.
- **Variant styled for rest state only.** A new variant inherits hover, focus, disabled, and dark-theme styles designed for its siblings, and some of them read wrong.
  Check: the new variant is verified across the full state matrix and every shipped theme, not just rest state in the default theme.
- **Composition replaced by configuration.** Props that embed content (`headerText`, `iconName`, `footerButtonLabel`) recreate slots as config; each new requirement adds two more props.
  Check: content and structure flow through children and slots; props configure behavior and appearance axes only.
- **Accessibility left to the consumer.** A component that is accessible only when every consumer remembers labels and roles ships inaccessible by default.
  Check: the laziest reasonable usage is accessible; required names are enforced by the API (required prop, dev-time warning), not by documentation.
- **Lifecycle states left undesigned.** Consumers hit loading, empty, error, and overflow states the component never defined, and improvise divergent versions.
  Check: the component defines its full set of reachable states, or is deliberately constrained not to have them.

## Escalation triggers (`needs-decision`)

- Breaking changes to shared or published component APIs: props, variants, slots, defaults, or exports other code consumes (also an ask-first boundary in the agent).
- Adding a component or headless library as a dependency (also an ask-first boundary in the agent).
- A new component whose responsibility overlaps an existing one's.

## What good looks like

- Variant axes are few, named, and orthogonal; every reachable state is designed.
- Consumers compose content; the component owns behavior and accessibility.
- API evolution is additive with deprecation paths, and defaults are stable.
