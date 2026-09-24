# .pi

This directory exists so that pi-review finds `REVIEW_GUIDELINES.md` at the repository root: it reads the guidelines only from a directory that also holds a `.pi/`, and stops walking there.

Keep it free of anything pi treats as project config (`settings.json`, `extensions/`, `skills/`, `prompts/`, `themes/`, `SYSTEM.md`, `APPEND_SYSTEM.md`), or every session in this checkout turns into a trust prompt.
