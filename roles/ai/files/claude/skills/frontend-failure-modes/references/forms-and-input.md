# Forms and input

When to read: the brief or diff touches forms, inputs, validation, submission flows, or file uploads.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Client and server validation drift.** Rules enforced only client-side are bypassable; rules that differ produce "valid here, rejected there" dead ends.
  Check: the server is authoritative; client validation mirrors it (shared schema where the project has one); server rejections render as field errors, not a generic toast.
- **Double submit.** A slow response plus an impatient user creates the resource twice; disable-on-click alone leaves the button dead after a failed request.
  Check: submission is guarded by in-flight state and re-enabled on failure; the operation is idempotent end to end (pair with the backend's idempotency-key pattern).
- **Unsaved work destroyed.** Navigation, modal close, or a refresh that silently discards a half-filled form is data loss.
  Check: forms long enough to hurt warn before discarding dirty state or persist drafts; which one is the project's convention.
- **Errors detached from fields.** A summary at the top or a toast without field-level association makes users hunt, and tells screen readers nothing.
  Check: each error renders at its field, wired with `aria-describedby` and `aria-invalid`; failed submit moves focus to the first invalid field; messages say how to fix, not just that it is invalid.
- **Autofill and IME broken.** Custom inputs that fight browser autofill, or Enter handlers that fire during IME composition, break address forms and CJK input.
  Check: inputs carry `autocomplete` attributes; key handling respects composition events; exercise the form with autofill, not only typed input.
- **Premature or nagging validation.** Validating every keystroke before the user finishes shouts at them mid-thought.
  Check: validate on blur or submit first, then re-validate eagerly only for fields already marked invalid.
- **Type-mangled values.** Numeric inputs returning strings, timezone conversion at the input boundary, and inconsistent trimming corrupt data on the way in.
  Check: parse and normalize once at the form boundary; the submitted payload's types match the contract exactly.
- **Upload edges unhandled.** File inputs without client-side size and type checks that mirror the server's, and long uploads without progress or a working retry, fail exactly when users care most.
  Check: client limits match server limits; large uploads show progress and recover from rejection with a clear path to retry.

## Escalation triggers (`needs-decision`)

- Validation rules the brief leaves undefined for user-visible behavior.
- Adding or changing draft-persistence or autosave semantics.
- Legal, financial, or destructive submissions with no review or undo step defined in the brief.
- Any flow where discarding user input is the intended behavior: confirm it, do not assume it.

## What good looks like

- The form cannot lie: client checks mirror the server, and server errors land on the fields that caused them.
- Submitting twice, losing the network mid-submit, or refreshing never duplicates or destroys data.
- Keyboard, autofill, IME, and screen readers all complete the form without workarounds.
