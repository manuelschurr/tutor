# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A standalone Claude Code plugin: `tutor`. The plugin lives here as its own repository and is installed via the [`c200v-marketplace`](https://github.com/manuelschurr/c200v-marketplace) catalog.

The plugin's purpose: take an individual learner from "I want to know more about topic X" to actually knowing more about topic X, through a personalized, adaptive curriculum delivered as guided study sessions inside Claude Code. One invoking user, multi-session, multi-course. Everything the plugin produces is personal, not published.

## Plugin anatomy

```
tutor/
  .claude-plugin/plugin.json  — plugin metadata, version, description
  README.md                    — user-facing docs
  agents/                      — custom agent type definitions (subagents the skills dispatch)
  commands/                    — slash command definitions (thin dispatchers to skills)
  skills/                      — SKILL.md files (the actual skill logic)
  scripts/                     — Python scripts + tests (currently the concept-graph validator)
  templates/                   — markdown scaffolds filled in by subagents at runtime
```

## High-level architecture

Two slash commands: `tutor:create` (build phase) and `tutor:study` (study phase). Each dispatches a skill. Skills orchestrate a small catalog of custom agent types:

- `researcher` — focused web research on one question, dispatched in parallel
- `graph-builder` — initial concept graph generation (runs once per course)
- `graph-mutator` — surgical edits to `concepts.dot` with mandatory backup + validation
- `outline-builder` — turns the approved graph into a chapter outline and stub files
- `chapter-expander` — expands a stub chapter into a full lesson plan (briefing, must-cover checklist, probing bank, quiz)

Courses live under `~/.claude/learning/<slug>/` by default. Each course folder is plain text (markdown, DOT, JSON) and can be tracked in git if the user wants.

## Commands and skills

Commands (`commands/*.md`) are thin dispatchers — they name the skill and pass through `$ARGUMENTS`. The real logic lives in `skills/<name>/SKILL.md`. When changing behavior, edit the skill; only touch the command if the dispatch metadata changes.

Skills are pure Markdown instructions, not code. They are loaded by Claude Code at runtime and followed as-is. Edit them like documentation — clarity and precision matter more than brevity.

## The concept graph is ground truth

Every course has a `concepts.dot` file that every subagent grounds against. The file follows a strict schema enforced by `scripts/validate-concept-graph.py`:

- Each node has `label`, `taxonomy`, `status` (one of `pending` / `covered` / `shaky`), `chapter`
- Edge direction: `A -> B` means "A depends on B"
- DAG (no cycles)
- No taxonomy category holds more than 30% of nodes
- Labels are unique

**Any mutation to `concepts.dot` goes through `graph-mutator`**, which follows backup → edit → validate → commit-or-revert. This is non-negotiable. Never edit `concepts.dot` directly.

## Python dependencies

`scripts/validate-concept-graph.py` requires `pydot` and `networkx` (pure Python, pip-installable). Graphviz CLI (`dot`) is an optional soft dependency for rendering `concepts.png` images — the validator itself doesn't need it. The plugin checks for these at first run.

## Tests

`scripts/test_validate_concept_graph.py` is a pytest suite for the validator. Run with `pytest scripts/test_validate_concept_graph.py -v`. All tests must pass before merging any changes that touch the validator.

## Conventions

- **Bump `version` in `.claude-plugin/plugin.json` on every change** to the plugin's skills, commands, agents, scripts, or templates. Claude Code checks this to decide whether the cached copy is stale.
- **Don't add new skills, commands, or agents without discussing with the maintainer first.**
- The `templates/` directory contains markdown scaffolds subagents fill in at runtime. Evolving the file format = editing these templates.
- Sessions are sequential — subagents are dispatched serially except for `researcher`, which is always dispatched in parallel when multiple questions need answering.

## Marketplace integration

This plugin is listed in the [`c200v-marketplace`](https://github.com/manuelschurr/c200v-marketplace) catalog by URL. When you bump the version here, also bump the corresponding entry in that marketplace's `marketplace.json` so users see the new version on their next refresh.
