---
description: 'Require provenance reporting for tools, instructions, skills, and sources'
applyTo: '**'
---

# Change Provenance Reporting

## Mandatory Output Section
- For every task that modifies files matching `applyTo`, include a `## Change Provenance Report` section in the final response.
- If a category has no entries, write `None`.

## Required Categories
- `MCP tools used`: List each MCP tool that was actually used.
  - Include: tool name, why it was used, and what it acted on.
- `Instructions applied`: List every instruction file that influenced decisions.
  - Include: file path and the key rule applied.
- `Skills used`: List each skill consulted.
  - Include: skill name and how it affected the output.
- `Other sources`: List all additional sources used.
  - Include: attachments, workspace files, subagent outputs, and web/official docs links.
- `Assumptions and gaps`: List assumptions and any areas not validated.
- `Validation run`: List checks performed (tests, lint, build, or manual checks) and outcomes.

## Reporting Rules
- Report only items actually used in the task.
- Do not invent tools, instructions, skills, sources, or validations.
- Distinguish sourced facts from assumptions.
- Keep entries concise and specific.
- Use clickable paths for local files and full URLs for web sources.

## Examples
- ✅ Good: `- tool: runSubagent (Official Docs Researcher) | purpose: gather current official guidance | target: AI transparency policy references`
- ✅ Good: `- instruction: .github/instructions/repo-research.instructions.md | rule: run Official Docs Researcher before modifying instructions/**`
- ❌ Bad: `Used several tools and docs` (not specific)
- ❌ Bad: `Validated everything` (no concrete checks)
