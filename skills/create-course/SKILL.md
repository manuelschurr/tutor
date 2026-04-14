---
name: create-course
description: Use when the user invokes /tutor:create to build a new personalized course on a topic. Runs research, interviews the learner, builds a concept graph and outline, writes stub chapter files, and prepares the course for /tutor:study. Run once per course.
---

# Create Course — Build a Personalized Learning Journey

## Overview

Build a new personalized course on a topic the user wants to learn. This is a collaborative, research-grounded process: the agent does initial research, interviews the user with informed questions, does deeper research, generates a concept graph, proposes an outline, and writes stub chapter files. At the end of this skill, chapter 1 is also expanded in full so the user can immediately start studying via `/tutor:study`.

The course lives at `~/.claude/learning/<slug>/` by default, or at a user-supplied path if `--path <dir>` was provided in `$ARGUMENTS`.

## When to use

- The user invoked `/tutor:create <topic prompt>`.
- The user says "I want to learn about X" and you recognize they want a structured course rather than ad-hoc answers.

**Do not run this skill if a course with the same slug already exists** under `~/.claude/learning/`. Tell the user the slug is taken and offer to append a suffix or let them pick a new slug.

## Checklist

Complete in order:

1. **Parse arguments.** Extract the topic prompt and optional `--path`. If no topic given, ask for one.
2. **Derive a slug** from the topic prompt. Check for collisions in `~/.claude/learning/index.json` and suffix with `-2`, `-3`, etc. if needed.
3. **Light-scan research (parallel).** Dispatch 3–5 `researcher` agents in parallel for high-level questions about the topic. Findings inform the interview. Hold findings in working context; do not write to disk yet.
4. **Interview the user** with informed questions. One question at a time. Capture: background, goals, depth, scope in/out, time budget. Mirror back understanding before proceeding.
5. **Deep research (parallel).** Dispatch 8–15 `researcher` agents in parallel based on interview answers. Collate returns into `<course-path>/research/build-phase-summary.md`.
6. **Create the course folder structure** and write `course.md` from the template using interview data.
7. **Generate the concept graph.** Dispatch `graph-builder` once. Present the validated graph + PNG to the user. Accept adjustments via `graph-mutator` dispatches until the user approves.
8. **Generate the outline and stubs.** Dispatch `outline-builder` once. Present `outline.md` to the user. Accept adjustments (edit outline.md + re-run `graph-mutator` for chapter reassignments if needed) until the user approves.
9. **Register the course** in `~/.claude/learning/index.json`.
10. **Expand chapter 1.** (Covered in detail in Slice 4; for this slice the step is a stub — see Task 16.)
11. **Hand off.** Tell the user how to start studying: `/tutor:study <slug>` (or just `/tutor:study` since this course is now `most_recent`).

## Step 1 — Parse arguments

`$ARGUMENTS` contains the user's topic prompt, possibly with `--path <dir>` flags. Parse:

- Extract `--path <dir>` if present; default course path is `~/.claude/learning/<slug>/`.
- Extract the rest as the topic prompt.
- If the topic prompt is empty or trivially short (<10 chars), ask: "What would you like to learn about? Feel free to include focus areas, depth preferences, and anything else that shapes what you want."

## Step 2 — Derive the slug

Generate a slug from the topic prompt:

- Lowercase.
- Replace whitespace and punctuation with `-`.
- Collapse multiple `-` into one.
- Trim to 40 chars max.
- Strip leading/trailing `-`.

Examples:
- "I want to know more about remote sensing, with a focus on SAR" → `remote-sensing-focus-sar`
- "Rust async" → `rust-async`

Check `~/.claude/learning/index.json` for collisions. If the file does not exist, create it with an empty `{"courses": [], "most_recent": null}` structure. If the slug collides, try `<slug>-2`, `<slug>-3`, etc. Tell the user the final slug before proceeding.

## Step 3 — Light-scan research

Derive 3–5 high-level research questions from the topic prompt. Examples for "remote sensing with SAR focus":

- "What are the main subfields of remote sensing today?"
- "What is synthetic aperture radar at a high level, and what are its major applications?"
- "What are the key missions and platforms currently flying SAR sensors?"
- "What are the typical prerequisites someone needs to understand SAR fundamentals?"

**Dispatch ALL light-scan researchers in parallel.** Make multiple Agent tool calls in a single message — one per question. Each call uses `subagent_type: "researcher"` and a per-call prompt containing only:

- The question
- One line of course context ("This is for a personal course on <topic>")

Do not write any files at this step. Hold the structured returns in working context so they can inform the interview.

## Step 4 — Interview the user

With light-scan findings in hand, conduct a focused interview. Rules:

- **One question at a time.** Do not batch multiple questions.
- **Multiple-choice preferred** when possible (easier to answer).
- **Use the light-scan findings to ask informed questions.** Not generic "what aspects are you interested in?" — specific "you mentioned SAR — are you more interested in the physics, the missions and platforms like Sentinel-1 and ICEYE, or the processing pipelines like SNAP and ISCE?".

Topics to cover (not necessarily in this order):

1. **Background** — what does the learner already know? (related topics, level of prior exposure)
2. **Goals** — why do they want to learn this? (career, personal interest, project, curiosity)
3. **Depth** — how deep do they want to go? (overview / working knowledge / deep expertise)
4. **Scope inclusions** — what aspects are definitely in?
5. **Scope exclusions** — what aspects are definitely out?
6. **Time budget** (optional) — roughly how much time they're willing to invest.

After each answer, reflect back briefly to confirm you understood. Do not move to the next question until the current one lands.

When you think the picture is complete, summarize it in one compact paragraph and ask: "Did I get this right? Anything to adjust before I dig into research?" Only proceed when the user confirms.

## Step 5 — Deep research (parallel)

Based on the interview, derive 8–15 focused research questions. They should target the specific subfields, concepts, applications, and prerequisites the user cares about. Skip things the user excluded.

**Dispatch ALL deep-research researchers in parallel.** Each gets one question and the course context summary.

**As returns arrive, collate them.** Write the consolidated file `<course-path>/research/build-phase-summary.md` yourself. The file should organize findings by theme, not by question, so the graph-builder has a coherent view. Suggested structure:

```markdown
# Build-Phase Research Summary

## Topic overview
<condensed synthesis across all research returns>

## Subfields and taxonomy suggestions
<what subfields exist, how they relate>

## Key concepts and dependencies
<concepts the graph should cover, with notes on prerequisite relationships>

## Common learner pitfalls
<misconceptions, hard parts, pre-requisites learners often lack>

## Sources
<de-duplicated list of all sources cited across all research returns>
```

Flag any low-confidence areas in a final "## Flags and uncertainties" section.

## Step 6 — Create the course folder

Create `<course-path>/` (default `~/.claude/learning/<slug>/`) with subdirectories:

```
<course-path>/
├── chapters/
└── research/
```

Write `<course-path>/course.md` by copying the template from `<plugin-path>/templates/course.md` and filling in the placeholders:

- `<SLUG>` — the derived slug
- `<ISO_TIMESTAMP>` — current timestamp in ISO 8601
- `<TITLE>` — a descriptive title derived from the topic and interview (not the raw prompt)
- Learner profile sections — from interview
- Scope sections — from interview
- Design rationale — leave as a comment placeholder; you'll fill this in after the outline is approved

(The research file `research/build-phase-summary.md` was already written in Step 5.)

## Step 7 — Generate and review the concept graph

Dispatch `graph-builder` once:

```
Agent({
  subagent_type: "graph-builder",
  prompt: "Build the initial concept graph for the course at <course-path>. Course description is at <course-path>/course.md. Research summary is at <course-path>/research/build-phase-summary.md. Validator script is at <plugin-path>/scripts/validate-concept-graph.py. Follow your standard contract; return the summary when done."
})
```

When graph-builder returns:

1. Read the validated `<course-path>/concepts.dot` and `<course-path>/concepts.png` if present.
2. Present a natural-language summary of the graph to the user: "I built a graph of <N> concepts in <M> taxonomy categories. The deepest dependency chain runs through: <chain>. Foundational concepts are: <list>. Here's the rendered graph [reference PNG path if exists]. Anything you'd change?"
3. **Handle user feedback by dispatching `graph-mutator`** for each adjustment. Typical adjustments: add a concept, drop a concept, rename a label, change an edge, rebalance taxonomy. Each dispatch is one mutation.
4. Loop until the user approves.

## Step 8 — Generate and review the outline

Dispatch `outline-builder` once:

```
Agent({
  subagent_type: "outline-builder",
  prompt: "Build the outline and stub chapter files for the course at <course-path>. Concept graph is at <course-path>/concepts.dot (validated). Course description is at <course-path>/course.md. Use the template at <plugin-path>/templates/chapter-stub.md. Validator script is at <plugin-path>/scripts/validate-concept-graph.py. Follow your standard contract; return the summary when done."
})
```

When outline-builder returns:

1. Read `<course-path>/outline.md` and the stub files.
2. Present the outline to the user: "Here's the proposed curriculum: <N> chapters. Chapter 1 covers <titles and concept counts>, chapter 2..., ..., chapter N covers .... Anything you'd change?"
3. Handle feedback:
   - **Chapter-level changes** (reorder, merge, split, drop, replace) — edit `outline.md` directly and re-run `graph-mutator` to update concept chapter assignments. After each change, re-run the validator with `--outline`.
   - **Concept additions** — dispatch `graph-mutator` to add the concept, then manually reassign it to a chapter and update the outline.
4. Loop until the user approves.
5. After approval, fill in the "Design rationale" section of `course.md` by writing 1–3 paragraphs explaining the shape of the course (why this chapter count, why this balance, what was emphasized or de-emphasized, why).

## Step 9 — Register the course

Update `~/.claude/learning/index.json`:

- Append the new course entry: `{slug, path, title, created_at, last_studied_at: null, current_chapter: 1, total_chapters: <N>, status: "in_progress"}`.
- Set `most_recent` to the new slug.

## Step 10 — Expand chapter 1

Chapter 1 is expanded in full during `/tutor:create` so the user can start studying immediately. All other chapters are expanded lazily at study time in `/tutor:study`.

### Step 10.1 — Per-chapter research for chapter 1 (parallel)

Read the chapter 1 stub (`<course-path>/chapters/01-<slug>.md`). Derive 3–6 focused research questions from the stub's "What the agent will research and explain when expanded" bullets and the chapter's concept list (which you can cross-reference in `<course-path>/concepts.dot`).

**Dispatch the researchers in parallel.** Each gets one question plus the course context summary. All in a single message with multiple Agent tool calls.

As returns arrive, collate them into `<course-path>/research/chapter-01-research.md` using this structure:

```markdown
# Chapter 01 Research

## Concepts covered
<list the concepts from the chapter>

## Research question 1: <question>
<key findings as bullets>

## Research question 2: <question>
<key findings as bullets>

...

## Sources
<de-duplicated list>

## Flags
<any low-confidence areas or contradictions>
```

### Step 10.2 — Dispatch chapter-expander

```
Agent({
  subagent_type: "chapter-expander",
  prompt: "Expand chapter 1 of the course at <course-path>.

Stub file: <course-path>/chapters/01-<slug>.md
Research file: <course-path>/research/chapter-01-research.md
Course description: <course-path>/course.md
Outline: <course-path>/outline.md
Concept graph: <course-path>/concepts.dot
State file: <course-path>/state.json
Template: <plugin-path>/templates/chapter-expanded.md

Adaptation context:
- This is the first chapter of the course; no prior quiz data exists.
- Interest signals: none yet.
- Special requests from user: <any specific asks captured during the create flow, or 'none'>.

Follow your standard contract. Return when the chapter file has been rewritten from stub to expanded form."
})
```

### Step 10.3 — Integrate the return

When chapter-expander returns:

1. Read the expanded `<course-path>/chapters/01-<slug>.md` and spot-check:
   - Frontmatter has `status: expanded` and an `expanded_at` timestamp.
   - Briefing section is present and non-empty.
   - Must-cover checklist covers all the chapter's concepts.
   - Probing questions bank has 8–15 items.
   - End-of-chapter quiz has 5–8 questions.
2. If any spot check fails, ask the chapter-expander to fix the missing section (one targeted retry).
3. Initialize `<course-path>/state.json`:

```json
{
  "schema_version": 1,
  "course_slug": "<slug>",
  "created_at": "<ISO_TIMESTAMP>",
  "last_studied_at": null,
  "current_chapter": 1,
  "chapters": [
    {
      "id": 1,
      "status": "ready",
      "session_count": 0
    }
  ],
  "interest_signals": [],
  "shaky_concepts_global": []
}
```

Mark chapter 1's status as `"ready"` (not `"in_progress"` — the user hasn't started studying yet).

## Step 11 — Hand off

Tell the user:

```
Course `<slug>` is ready. Chapter 1 has been expanded and is ready to study.

Next: run `/tutor:study` to begin your first session. I'll walk you through chapter 1.

You can also:
- Run `/tutor:study <slug>` to load a specific course if you have multiple.
- Open `<course-path>/outline.md` to skim the curriculum.
- Open `<course-path>/concepts.png` to see the concept graph rendered (if Graphviz was installed).
```

## Error handling

- **Missing dependencies** (pydot, networkx): detect at step 1 by trying to import them in a quick Python check. If missing, surface instructions and stop.
- **Graphviz CLI missing**: not fatal. Mention it once and continue — PNG rendering is skipped.
- **Research subagent failure**: retry once with a reformulated question. If still failing, surface to user and continue with remaining researchers.
- **Graph validation failure during graph-builder**: graph-builder is supposed to handle retries internally. If it returns failure anyway, surface to user and offer to retry.
- **Graph-mutator failure**: surface the validation violations to the user, revert any changes, ask how to proceed.
- **Disk write failures**: surface immediately; do not continue with a half-built course folder.

## Constraints

- **Researchers are always dispatched in parallel** when more than one is needed.
- **Each graph-mutator dispatch is one mutation.** Do not batch unrelated changes.
- **The main agent never pastes a subagent's full output** into the conversation — read the structured return, spot-check files, surface findings in natural language.
- **Do not proceed past a user approval gate without explicit confirmation.** Graph approval and outline approval are hard gates.
- **`research/build-phase-summary.md` is written by the main agent**, not by any subagent.
