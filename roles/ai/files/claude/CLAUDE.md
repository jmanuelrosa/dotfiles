# Global Claude instructions

## Git commits

Do not write `Co-Authored-By: Claude …` (or any `🤖 Generated with` line) into commit message bodies, plan files, or HEREDOCs that produce commit messages. Attribution is handled at the Claude Code platform level via the `attribution` setting in `settings.json`; duplicating it in the message body produces the trailer even when attribution is configured to be empty.

This applies to direct `git commit -m` invocations and to any plan or skill that prescribes a commit message template.
