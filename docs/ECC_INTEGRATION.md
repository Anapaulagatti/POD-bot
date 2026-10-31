# ECC integration for PODBot (project-local)

Source: https://github.com/affaan-m/ECC (MIT; copyright 2026 Affaan Mustafa).
Reviewed selected files for this Python project, retrieved from the upstream repository on October 31, 2026.

The following upstream content is copied unmodified as project-scoped Claude Code skills and rules:

- `.claude/skills/python-testing/SKILL.md` (upstream `skills/python-testing/SKILL.md`)
- `.claude/skills/python-patterns/SKILL.md` (upstream `skills/python-patterns/SKILL.md`)
- `.claude/skills/tdd-workflow/SKILL.md` (upstream `skills/tdd-workflow/SKILL.md`)
- `.claude/rules/common/security.md` (upstream `rules/common/security.md`)
- `.claude/rules/python/testing.md` (upstream `rules/python/testing.md`)

This **does not install ECC globally on the user's Windows machine** nor does it install the full ECC plugin, agents or hooks. Project skills are read by supported coding agents when opened in the project with project skill discovery enabled. There is no build-time dependency on ECC; it is only for developers.

For the complete native ECC plugin on your own Windows Claude Code, use the **official** marketplace installation **instead** of this scoped skill copy to avoid duplicated skill definitions:

```text
/plugin marketplace add https://github.com/affaan-m/ECC
/plugin install ecc@ecc
```

Or see upstream official guided setup (Node.js, Git, Claude Code required): `npx ecc-universal@2.2.3 setup`. Review npm packages before executing. Do not run both install methods. If installing full native ECC for the project, remove or disable duplicated `.claude/skills/` entries. The project-scoped files alone need no npm runtime.

No external scripts, hooks, auto-executing commands or telemetry were imported from ECC. Review skill Markdown as untrusted third-party content when editing it.
