# Forms: Detailed Rules

Complete form implementation rules for accessible, usable web forms.

## Input Configuration

- Set `autocomplete` attribute with meaningful value on all inputs
- Use meaningful `name` attributes (not `input1`, `field2`)
- Use correct `type`: `email`, `tel`, `url`, `number`, `password`, `search`
- Set `inputmode` for mobile keyboards: `numeric`, `decimal`, `tel`, `email`, `url`
- Disable spellcheck on emails, codes, and usernames: `spellCheck={false}`
- `autocomplete="off"` on non-auth fields where browser autofill is unhelpful

## Labels & Hit Targets

- Labels must be clickable: use `htmlFor` or wrap the control inside `<label>`
- Checkboxes and radios: label + control share a single hit target
- Placeholders end with `…` and show an example pattern (e.g., `Search…`, `john@example.com`)
- Never use placeholder as the only label

## Paste & Input Freedom

- Never block paste (`onPaste` with `preventDefault` is an anti-pattern)
- Let users paste passwords, emails, codes, and verification tokens

## Submit & Loading

- Submit button stays enabled until the request starts
- Show spinner or loading indicator during the request
- Disable submit only while request is in-flight (not preemptively)

## Error Handling

- Show errors inline next to the relevant field
- Focus the first error field on form submit
- Error messages include what went wrong and how to fix it
- Don't clear valid fields when there's an error elsewhere

## Unsaved Changes

- Warn before navigation when form has unsaved changes
- Use `beforeunload` event or router-level guards
- Provide explicit save/discard actions

## Accessibility

- All form controls need `<label>` or `aria-label`
- Group related fields with `<fieldset>` and `<legend>`
- Use `aria-describedby` to link error messages to inputs
- Required fields: use `required` attribute, not just visual indicators
- `aria-invalid="true"` on fields with errors
