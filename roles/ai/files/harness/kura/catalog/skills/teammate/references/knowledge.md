# Knowledge store

A personal, unversioned record of what has been verified about one product, so the next session starts from it instead of from zero.
It lives at `<workspace root>/.teammate/`, found as described in `profile.md`, and is never placed inside a published repo.

## Layout

```
.teammate/
  PROFILE.md    repos, sources, approvals (see profile.md)
  INDEX.md      the map: one line per area or topic with a link, a "Not yet mapped" section, last surveyed sha per repo
  areas/        one page per repo or subsystem
  topics/       how, why and trace findings worth keeping
  GLOSSARY.md   the product's language, in domain-modeling's GLOSSARY-FORMAT.md
  learner.md    what the user already understands
  evals/        the user's private acceptance cases for this product
```

Create a file only when the first entry for it is approved.

## Page shape

```markdown
---
anchors:
  - repo: <dir name>
    sha: <short sha at verification>
    paths: [<files or dirs the claims rest on>]
verified: <date>
---

# <title>

<claims, each keeping its evidence label and citation from the answer>

## Open questions
<what is still unknown, and where it was searched>
```

`INDEX.md` lines are gists with links, never copies of the page.
`learner.md` records what the user showed they understand, prior knowledge they mentioned, and misconceptions corrected, each dated; a changed entry is marked superseded with a link to its replacement, never deleted.
Coverage is not understanding: an explanation the user only read is not a learner entry.

## Reading

Read `INDEX.md` first, then only the page the question needs.
Before trusting a page, check each anchor: `git -C <repo> log --oneline <sha>..HEAD -- <paths>`.
Empty output: the claims stand as Verified behavior at the current HEAD.
Any output: the page is stale. Present its claims as "verified at <sha>", name how many commits touched the anchored paths since, and re-verify the claims the answer depends on before stating them as current.
A stored page is never itself a citation for current behavior; the code it points to is.

## Writing: the store gate

1. Collect what is worth keeping during the thread: verified flows, resolved terms, why findings with their labels, contradictions, open questions. Skip anything the repo's own docs already say; link to them instead.
2. At a natural end of the thread, or on `/teammate save`, offer it once, as the exact content: the files to create or change and their text.
3. Write only after an explicit yes ("yes", "save it", "do it"). "Sounds good", "ok maybe" or silence is not a yes; ask once more or drop it.
4. Write with the file tools, not shell redirection, so the harness can show and confirm the write.
5. Never store secrets, credentials, customer or personal data, or direct-message text.

Glossary entries follow the same gate: propose the entry inline when a term resolves, write it with the next approved batch.

## Promotion

When a page would help the team, offer to turn it into a change to the repo's own docs (CONTEXT.md, an ADR, a README).
That is a normal change the user makes or asks for through their own commit and review flow, never a write by this skill.
