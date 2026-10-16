# Evidence labels

Every claim in a teammate answer carries exactly one of five labels.
The label decides the phrasing, so a reader can tell from the sentence alone how much weight it bears.
`why/references/epistemics.md` stays the authority for grading historical and inferred claims; these labels sit on top of its tiers and add the two kinds of evidence it does not separate.

| Label | Counts as evidence | Phrasing | Citation |
|---|---|---|---|
| **Verified behavior** | Current source, a test that pins the behavior, or a command actually run in this session | "X does Y." | `repo/path:line` at the HEAD recorded for the investigation |
| **Documented intent** | ADRs, CONTEXT.md, GLOSSARY.md, specs, `.claude/docs`, READMEs, a ticket's stated requirement | "The ADR says X is meant to Y." | Path or link, with the doc's date when it has one |
| **Historical evidence** | Commits, PR or MR bodies and reviews, ticket comments, chat threads, meeting notes | Follows `why`'s Direct and Supported tiers | Short sha, `owner/repo#N` or `group/repo!N`, ticket key, permalink |
| **Inference** | Reasoning from the above that no source states | Follows `why`'s Inferred and Speculative tiers | The pieces it rests on |
| **Unknown** | Nothing found after looking | "Searched A, B and C for D; found nothing." | The queries and sources tried |

## Rules

- Only code, tests and commands run in this session are Verified behavior. A ticket, PR body, review or chat thread is Documented intent or Historical evidence, however authoritative it sounds; "verified, PR #N" is a mislabel.
- A code comment is Documented intent, even beside the line it describes. What the code does is Verified behavior; the reason a comment gives for it is not.
- Memory and general knowledge are not evidence. Check it against a source in this session, or state it as Unknown with what would confirm it.
- A conclusion drawn from history (commit timing, who changed what) is Inference, even when every commit it rests on is real.
- A requirement is not an implementation. A ticket saying X should happen is documented intent; only the code or a run shows that it does.
- Current behavior is not original intent. Code shows what it does today, never why it was written that way.
- When documentation and code disagree, state both with their citations and label it a contradiction. Do not pick a winner, do not guess which one is stale, and do not call either "old", "outdated" or "out of date" unless the commit history read in this session shows it; the thread to offer is "check which changed last".
- Who the user is comes from a probe in this session (`gh api user --jq .login`, the profile), never from a home directory or path name. Until checked, write "reviewed by <login>", not "you".
- When two historical sources disagree, show both and say what each would imply.
- Record the branch and HEAD short sha when an investigation starts. A finding from another branch, an older version or a deleted file says so in the same sentence.
- Each gap names its own state: not fetched, fetched and empty, or probed and failed. Never merge two into "empty or not read".
- A citation points to something read in this session. A remembered or plausible path is not a citation; read it or drop it.
- Labels are for the reader, not decoration. In a short answer, one label per paragraph is enough when every sentence in it shares the label; a claim that differs gets its own.
- The phrasing rules and banned words in `why/references/epistemics.md` apply to every label, not only to `why` answers.
