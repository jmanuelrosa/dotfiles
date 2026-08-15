# Craft and distinctiveness

When to read: the brief or diff touches a new surface, a visual direction, a landing or marketing page, a re-skin, or any screen a user forms a first impression of.

The other references in this skill ask whether the design is correct.
This one asks whether it is any good.
A screen can pass every other checklist here and still be the median answer, because correctness is a floor and nothing in a floor makes a choice.

The refusals below are drawn from the craft floor of [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (Apache-2.0), which catalogues what machine-generated interfaces reach for by default.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **No dominant element.** When the largest thing on screen is roughly twice the size of the smallest, nothing leads and the eye is given no entry point; the page reads as a list of equally important things, which is what a document looks like, not what a product looks like.
  Check: the type and element scale spans at least 6x somewhere on the surface, and the largest element is the one the thesis names.
- **One family in several weights, presented as typography.** Changing the weight of a single face is a hierarchy device, not a type decision, and it leaves the page with no voice.
  Check: at least two faces with stated, distinct roles; a display face chosen for character rather than neutrality; the pairing named in the report.
- **A palette of three.** A ground, an ink, and one accent is the minimum required to not be monochrome, which is a different thing from a palette.
  Check: the palette is stated with a count, a temperature, and a strategy tier (restrained, committed, full, drenched), and the tier is a choice the report defends.
- **No material.** Flat fills and 1px borders throughout means the surface has no substance: no grain, gradient, photography, texture, blur, or depth vocabulary.
  Check: the surface treatment is named, and layering and depth are expressed by something other than a border.
- **Nothing reaches an edge.** Every element inside equal margins produces a centered column of boxes, which is the shape of a generated document.
  Check: at least one element is full-bleed or deliberately breaks the container, or the report defends the containment as the direction.
- **The subject's own material is absent.** A product about maps with no map, about music with no waveform, about money with no ledger: the one source of distinctive imagery is the subject's own world, and a design that omits it would work equally well for any other subject.
  Check: name what from the subject's world appears on screen; if the strings could be swapped to another product without redrawing anything, this fails.
- **The characteristic artifact is buried.** The most interesting thing the product has (an elevation profile, a route line, a waveform, a diff) rendered small, boxed, and far down the page.
  Check: the subject's signature artifact is either the hero or has a stated reason not to be.
- **A kicker or eyebrow above a heading.** A small caps label sitting above a title adds a hierarchy level that carries no information and is the single most reliable tell of generated layout.
  This one is a ban, not a default: no brief earns it back.
  Check: no eyebrow, kicker, or standalone caps label immediately preceding a heading.
- **Same-size cards as the page structure.** A grid or stack of identical containers, each holding an icon, a heading, and a line of text, is the lazy container: it flattens every item to equal weight and defers every layout decision.
  Nested cards are always wrong.
  Check: no card grid as the primary structure, and no card inside a card.
- **Gradient text, and monospace as a costume.** Gradient fills on type substitute for a hierarchy decision, and monospace applied to numbers or labels to signal "technical" is a costume rather than a typographic choice.
  Check: emphasis comes from weight, size, or position; monospace appears only where character alignment is functionally required (tabular data, code, diffs).
- **Emoji or Unicode glyphs standing in for an icon system.** They render differently per platform, carry another vendor's visual language, and cannot be styled with the design.
  Check: icons come from one set that the design controls.
- **The rendition default.** Machine-generated design converges on a small number of looks that appear regardless of subject: a warm cream ground near `#F4F1EA` with a high-contrast serif and a terracotta accent; a near-black ground with a single acid-green or vermilion accent; a broadsheet layout of hairline rules, zero radius, and dense columns.
  All three are legitimate for some briefs and none of them is a choice when it arrives unbidden.
  Check: where the brief pins a direction, follow it; where it leaves an axis free, that freedom is not spent on one of these three, and the report says what it was spent on instead.
- **Measure and tracking left at defaults.** Long lines and untouched letter-spacing at display sizes are the two settings that most reliably make competent type look unconsidered.
  Check: body measure lands in 65 to 75 characters, and display sizes carry deliberate negative tracking rather than the face's default.
- **Boldness spread evenly.** A design that makes a move on every axis at once reads as loud rather than considered, and the moves cancel each other.
  Check: the report names one signature element carrying the boldness, and can point at what was kept quiet to let it land.

## Escalation triggers (`needs-decision`)

- The brief pins a direction that is one of the rendition defaults; follow it, and note that it was the brief's choice rather than yours.
- The project has an established design system whose own idiom breaks a refusal here: the system wins, and the conflict is reported rather than silently resolved.
- A distinctive direction requires a dependency (a web font, an icon set, an image asset pipeline), which is an ask-first boundary in the agent.
- The subject is not pinned down by the brief and cannot be inferred, so there is no world to draw from.

## What good looks like

- The surface is about one thing, and a stranger could say what it is from the first viewport alone.
- One element carries the boldness and everything around it is disciplined enough for that to register.
- The subject's own material is visible, and the design would have to be redrawn to serve a different product.
- Every axis (scale, type, palette, material, bleed, grid, density, motion) has a stated position, and none of them reads "whatever the framework does".
