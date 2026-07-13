# CSS architecture

When to read: the brief or diff touches stylesheet structure, specificity, cascade layers, custom properties, or z-index.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Specificity escalation.** Beating an existing selector with a more specific one, or with `!important`, starts an arms race the next engineer continues.
  Check: new rules match the flattest prevailing idiom; overrides go through the system's mechanism (layer order, tokens, the component's variant API), and `!important` appears only where the project already sanctions it, never on themeable or text properties where it blocks token overrides and user adjustments.
- **Magic z-index.** A 999 wins today, so tomorrow someone writes 9999; stacking becomes archaeology.
  Check: z-index values come from the project's scale; a new stacking need is solved with a stacking context (`isolation: isolate`) before a bigger number.
- **Unscoped styles leaking.** A global tag or utility selector added for one component restyles strangers, and removing it later is unsafe.
  Check: new styles are scoped by the project's mechanism (modules, scoped attributes, naming convention, layers); a global addition is a deliberate base-layer change.
- **Unlayered CSS in a layered system.** Unlayered styles beat every `@layer` for normal declarations; a new file outside the layers silently outranks the whole system.
  Check: in a layered codebase, new styles land in the correct layer; no unlayered CSS is introduced.
- **Selectors coupled to DOM structure.** Positional selectors (`div > div:nth-child(2)`) break on harmless markup edits, and deep descendant chains restyle nested strangers.
  Check: selectors target names, attributes, or parts, never positions or deep descent; a markup reorder should not restyle.
- **Custom property consumed without a fallback.** `var(--x)` where `--x` may be unset resolves to garbage or to invalid-at-computed-value behavior, and a typo'd name fails silently.
  Check: custom properties consumed outside their guaranteed scope carry fallbacks, and new property names are grep-verified against their definitions.
- **Override by accretion.** Adding a winning rule while the losing rule stays alive leaves contradictory declarations whose net effect nobody can read from the source.
  Check: when your new rule overrides one you own, edit or remove the old rule; the winning rule should be the only rule.
- **Shorthand resets siblings.** A `background` or `font` shorthand silently resets the longhand properties set elsewhere (background-image, line-height).
  Check: overrides use longhands unless resetting the whole group is the intent.
- **Variant styles far from their base.** The dark-mode, hover, or breakpoint override living in a distant file drifts from its base rule; edits update one and miss the other.
  Check: state and theme variants sit adjacent to their base rule per the project's idiom, or live in the token layer where no component rule is needed.

## Escalation triggers (`needs-decision`)

- Introducing a new styling mechanism beside the existing one (a new library is also an ask-first boundary in the agent).
- Adding a new step to the z-index scale (also an ask-first boundary in the agent).
- Restructuring layer order or the global base layer.

## What good looks like

- Specificity stays flat; the cascade is used deliberately through layers, tokens, and variants.
- Stacking is managed with contexts and a scale, not escalation.
- Every rule's scope is intentional: deleting a component deletes its styles.
