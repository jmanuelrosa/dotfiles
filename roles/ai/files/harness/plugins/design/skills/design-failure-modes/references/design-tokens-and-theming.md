# Design tokens and theming

When to read: the brief or diff touches design tokens, semantic aliases, theme definitions, dark mode, or brand values.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Raw value beside the token system.** A hex, px, or ms literal in component styles forks the system: theme changes and rebrands miss it, and it drifts from the value it copied.
  Check: every value in the diff resolves to a token or scale step (grep the diff for hex, `rgb(`, `hsl(`, and bare lengths); a value the system lacks is a token proposal, not an inline literal.
- **Component styled from the raw palette.** Referencing a palette entry directly encodes the color, not the intent; when the theme remaps that hue, the component keeps the old meaning.
  Check: components consume semantic aliases (surface, text-muted, border-danger); raw palette references live only inside theme definitions.
- **Token defined in one theme only.** A semantic token added to the default theme but not the others resolves to nothing, or to an inherited wrong value, and fails only when someone switches.
  Check: every token added or renamed resolves in every shipped theme; grep the other theme sources for the same key.
- **Semantic token repurposed instead of added.** Reusing an existing alias for an unrelated meaning couples the two; the next redesign of the original meaning restyles your surface.
  Check: the token's name still describes every usage after the change; a new intent gets a new alias, even when it points at the same value today.
- **Semantic token minted with a literal value.** A semantic token holding a raw value instead of an alias forks the source of truth; the next palette change silently skips it.
  Check: a new semantic or component token's value references a primitive token, not a literal; a new primitive is justified, not a near-duplicate of an existing one.
- **Theme styled with component overrides.** Per-component dark-mode rules instead of token value swaps make the Nth theme cost N component edits.
  Check: themes change token values, not component rules; a component free of theme conditionals is the goal.
- **Generated token outputs edited by hand.** Editing the build output (custom-property files, platform artifacts) instead of the source makes the next generation silently revert the change.
  Check: the edit lands in the token source and outputs are regenerated with the project's own command.
- **Rename without an alias path.** Renaming a consumed token breaks builds, or worse resolves silently to a fallback at runtime and ships unstyled UI.
  Check: renames keep the old name as a deprecated alias until consumers migrate; the alias is removed only when a grep for the old name comes up empty.
- **Value change with an unaudited blast radius.** Changing the resolved value of a widely consumed token restyles every consumer at once, including screens nobody enumerated.
  Check: scope the change to a new token, or escalate it (ask-first); once approved, list the consumers and verify the highest-traffic ones in every theme.
- **Half-tokenized system.** Colors tokenized while radii, shadows, borders, opacity, and durations stay hardcoded means the next brand change updates buttons and misses cards.
  Check: the diff's radii, shadows, and durations come from tokens wherever the system defines them.

## Escalation triggers (`needs-decision`)

- Renaming or removing a consumed token without a deprecation alias, or changing a consumed token's resolved value (also an ask-first boundary in the agent).
- Introducing a new theme dimension: a new theme, density mode, or high-contrast variant.
- A brand-level value change (brand palette, typefaces) the brief did not explicitly request (also an ask-first boundary in the agent).

## What good looks like

- Components read semantic aliases; themes are pure value maps; the palette appears only in theme definitions.
- Adding a theme touches token files only, with zero component edits.
- Token sources are the single source of truth; outputs are generated, never hand-edited.
- Every token's name still tells the truth about where it is used.
