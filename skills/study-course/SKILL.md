---
name: study-course
description: Use when the user invokes /tutor:study to run a study session on an existing tutor course. Loads the course state, walks the user through one or more chapter sessions (briefing, guided dialogue, quiz, meta-analysis, adaptation, next chapter), and persists progress. Run whenever the user wants to make progress on a course.
---

# Study Course — Guided Chapter Sessions

## Overview

Run a study session on an existing tutor course. Each session walks through one or more chapters in a tight loop: briefing → guided dialogue → end-of-chapter quiz → meta-analysis of shaky concepts → adaptation proposal for the next chapter. Sessions can span many chapters or exit cleanly after one.

The skill assumes the course was created by `/tutor:create` and lives in `~/.claude/learning/<slug>/` (or the path recorded in `~/.claude/learning/index.json`).

## When to use

- The user invoked `/tutor:study` (optionally with a course slug).
- The user says "let's study" or "let's continue the remote sensing course."

**Do not run this skill if no course exists.** If `~/.claude/learning/index.json` is missing or empty, tell the user: "You don't have any tutor courses yet. Run `/tutor:create <topic>` to start one."

## Checklist

One iteration of the chapter loop covers:

1. **Entry** — load course state, pick chapter, expand stub if needed
2. **Briefing** — paste the chapter's `## Briefing` section verbatim
3. **Transition** — follow the briefing's hook into dialogue
4. **Guided dialogue** — draw from probing questions, follow tangents, track must-cover privately
5. **Coverage check** — when the must-cover checklist is full, transition to the quiz
6. **End-of-chapter quiz** — paste questions verbatim, evaluate answers conversationally
7. **Meta-analysis** — classify shaky concepts against the outline
8. **State update** — persist `state.json` and update concept statuses via `graph-mutator`
9. **Adaptation prompt** — present the next chapter's stub, surface chapter-level changes explicitly
10. **Loop or exit** — on user approval start the next chapter; on "that's enough" exit cleanly

## Step 1 — Entry

### 1.1 Load the course

Read `~/.claude/learning/index.json`:

- If `$ARGUMENTS` is empty: load the course whose slug equals `most_recent`.
- If `$ARGUMENTS` is a slug: find that slug in `courses`. If not found, fuzzy-match against all slugs and offer the closest match. If the user rejects, list all courses and ask.

Set `<course-path>` from the matched entry.

### 1.2 Load state

Read `<course-path>/state.json`. Validate `schema_version == 1`. If the file is missing or corrupt, surface an error and stop.

### 1.3 Pick the chapter

The next chapter is `state.current_chapter`. Find its entry in `state.chapters`:

- If `status == "completed"`: this shouldn't happen — advance `current_chapter` by 1 and retry. If all chapters are complete, congratulate the user and exit.
- If `status == "ready"` or `"in_progress"`: proceed.

### 1.4 Expand the stub if needed

Read the chapter file at `<course-path>/chapters/NN-<slug>.md`. Check its frontmatter `status`:

- If `status: expanded`: skip to Step 2 (Briefing).
- If `status: stub`: run the expansion sub-flow (Steps 1.4a–1.4c) before proceeding.

#### Step 1.4a — Per-chapter research (parallel)

From the stub's "What the agent will research and explain when expanded" bullets and the chapter's concept list (cross-referenced in `<course-path>/concepts.dot`), derive 3–6 focused research questions.

**Dispatch researchers in parallel.** Multiple Agent tool calls in a single message. Each call: `subagent_type: "researcher"`, prompt contains the question plus the course context.

#### Step 1.4b — Collate research

As returns arrive, write `<course-path>/research/chapter-NN-research.md` using the same structure as the build-phase summary:

```markdown
# Chapter NN Research

## Concepts covered
<list>

## Research question 1: <question>
<findings>

...

## Sources
<list>

## Flags
<if any>
```

#### Step 1.4c — Dispatch chapter-expander

```
Agent({
  subagent_type: "chapter-expander",
  prompt: "Expand chapter NN of the course at <course-path>.

Stub file: <course-path>/chapters/NN-<slug>.md
Research file: <course-path>/research/chapter-NN-research.md
Course description: <course-path>/course.md
Outline: <course-path>/outline.md
Concept graph: <course-path>/concepts.dot
State file: <course-path>/state.json
Template: <plugin-path>/templates/chapter-expanded.md
Previous expanded chapter (for continuity): <course-path>/chapters/<prev-NN>-<prev-slug>.md

Adaptation context:
- Quiz performance from prior chapters: <summary from state.json — mention chapter scores and any global shaky concepts>
- Interest signals to honor: <list from state.json>
- Special requests from user: <anything the user said during the current session, or 'none'>

Follow your standard contract. Return when the chapter file has been rewritten from stub to expanded form."
})
```

When chapter-expander returns, spot-check the expanded file (frontmatter `status: expanded`, briefing present, must-cover present, probing bank present, quiz present). One targeted retry allowed if a section is missing.

**Before proceeding**, tell the user: "Expanding chapter NN now — this takes about a minute." Then wait for the dispatch. This is worth a deliberate message so the wait doesn't feel confused.

## Step 2 — Briefing

Read the `## Briefing` section of the expanded chapter file. **Paste it verbatim** to the user, optionally prefixed by a one-sentence opener:

> Alright, chapter NN — <Title>.
>
> <full briefing section verbatim>

Do not rewrite the briefing in your own voice. The chapter-expander already wrote it in deliverable tone; rewriting it costs tokens and drifts the voice.

After the briefing, pause for a moment — the user may want to react. If they don't, move to Step 3.

## Step 3 — Transition

The briefing ends with a hook into dialogue (e.g., "That's the headline. The interesting part is X — let's get into it."). Follow the hook naturally: ask the first probing question drawn from the Probing Questions Bank, or respond to whatever the user said after the briefing.

## Step 4 — Guided dialogue

This is the heart of the study session. Rules:

- **Draw from the Probing Questions Bank.** The bank is in the expanded chapter file under `## Probing Questions Bank`. You may adapt the wording slightly to fit conversation flow, but the question itself comes from the bank. Track which questions you've used so you don't repeat.
- **Track the Must-Cover Checklist privately.** The checklist is in the expanded chapter file under `## Must-Cover Concepts`. As the user demonstrates understanding of a concept, mentally check it off. Do not tell the user you're checking off items.
- **Watch for misconceptions.** The Common Misconceptions section lists what to look for. If you see one, use the response pattern to gently surface and correct it.
- **Follow tangents with the bookmark-and-return pattern.** If the user chases a topic, go with them as long as it's productive. The Anticipated Tangents section has pre-written bring-it-back hooks for common ones. When a tangent has been explored enough, use the hook: "we'll spend more time on this in chapter X — for now let's return to Y."
- **Capture interest signals.** If the user says "I'm particularly interested in X" or "I care about Y," remember it for Step 8.
- **Never read the chapter file verbatim** (except the Briefing in Step 2 and the Quiz questions in Step 6). Scaffolding sections are for you, not for the user.
- **Never reveal the probing bank, must-cover checklist, or the scaffolding structure.** From the user's perspective, this is a conversation with an expert.
- **Guide, don't wait.** Claude is always driving the conversation forward. When the user goes silent or says "okay, what's next," pick the next probing question.
- **Ask follow-ups on shaky concepts.** If the user's answer to a probe is partial or off-base, ask a different probing question on the same concept until it lands. Do not just mark it shaky and move on — try twice before giving up.

## Step 5 — Coverage check

When the must-cover checklist is full (all items landed through dialogue), explicitly transition:

> I think we've covered the spine of this chapter. Let me ask you a few questions to check what stuck.

If the user pushes back ("wait, I still have questions about X"), return to dialogue for that concept. Only move to the quiz when the user is ready.

## Step 6 — End-of-chapter quiz

Read the `## End-of-Chapter Quiz` section of the expanded chapter file. Ask the questions **one at a time**, pasted **verbatim**. After each answer:

- **Evaluate conversationally** — was the answer correct, partial, or off-base?
- **Give a brief explanation** — what was right, what was missing or wrong, why.
- **Move on** — no score-shaming.

Track per-question outcomes for the meta-analysis:

- `correct` — full credit
- `partial` — partial understanding, concept is shaky
- `off-base` — wrong, concept is shaky

When all quiz questions are done, announce the result in a low-key way:

> You got <N> of <M> right. <Any shaky concepts> came up as shaky — I'll keep that in mind as we plan the next chapter.

## Step 7 — Meta-analysis of shaky concepts

This is the new analytical step. Don't skip it.

### 7.1 Identify shaky concepts

From the quiz outcome:

- Concepts with all correct answers → `covered`
- Concepts with any partial or off-base answer → `shaky`

Remember to cross-reference concept IDs from the chapter file's `concepts:` frontmatter, not just labels.

### 7.2 Classify each shaky concept

For each shaky concept, read `<course-path>/outline.md` to find which upcoming chapters teach or build on it. Also look at `<course-path>/concepts.dot` to see which downstream concepts depend on it.

Classify:

- **Will be reinforced naturally** — an upcoming chapter already covers or builds on this concept. Log in `state.json` under `shaky_concepts_global` and `chapters[current].shaky_concepts`. Move on silently — don't mention it unless the user asks.
- **Won't be reinforced and is foundational** — no upcoming chapter covers it, but downstream concepts depend on it. Surface explicitly to the user: "You seemed shaky on <concept>, and the curriculum as laid out won't come back to it. Want me to reinforce it now, or fold it into chapter <X> where it'd be most useful?"
- **Won't be reinforced and is peripheral** — shaky but minor. Log silently, move on.

### 7.3 Act on user response

If the user chose "reinforce now": have a quick targeted dialogue on the concept (5–10 minutes). No new quiz — just a conversation that re-surfaces the idea with fresh probes.

If the user chose "fold into chapter X": note this in `state.json` as an interest signal (`{from_chapter: current, topic: concept_label, weight: "high"}`) so chapter-expander for chapter X picks it up when expansion runs.

## Step 8 — State update

Update `<course-path>/state.json`:

- Set `chapters[current].status = "completed"`
- Set `chapters[current].completed_at = <ISO_TIMESTAMP>`
- Set `chapters[current].quiz_score` and `quiz_total`
- Set `chapters[current].shaky_concepts` to the list of shaky concept IDs from meta-analysis
- Update `shaky_concepts_global` — append new shaky concepts (deduplicated), remove concepts that were shaky in earlier chapters but are now covered
- Append any interest signals captured during dialogue or meta-analysis to `interest_signals`
- Set `last_studied_at = <ISO_TIMESTAMP>`
- Advance `current_chapter` by 1 if not already at the end

Also update concept statuses in `<course-path>/concepts.dot` by dispatching `graph-mutator`. One dispatch can cover multiple status updates — describe them collectively in the brief:

```
Agent({
  subagent_type: "graph-mutator",
  prompt: "Update concept statuses in the graph at <course-path>/concepts.dot:
- Set status='covered' for: <list of covered concept IDs>
- Set status='shaky' for: <list of shaky concept IDs>

Course outline is at <course-path>/outline.md (pass as --outline). Validator script at <plugin-path>/scripts/validate-concept-graph.py. Follow your standard contract."
})
```

Also update `~/.claude/learning/index.json`:

- Set `most_recent = <current slug>`
- Update `last_studied_at` on the course entry
- Update `current_chapter` on the course entry
- If all chapters are complete, set `status = "completed"` on the course entry

## Step 9 — Adaptation prompt for the next chapter

If all chapters are complete, congratulate the user and offer to start a new course. Otherwise:

### 9.1 Decide adaptation strategy

Based on this chapter's quiz outcome, shaky concepts, and any captured interest signals, decide what (if anything) to change about the next chapter.

**Silent adjustments** (apply without asking):

- Rebalance emphasis within the next chapter's stub (update the bullets in the `## What the agent will research and explain when expanded` section)
- Add must-cover emphasis for reinforcement of shaky concepts from this chapter
- Add bullets for concepts the user expressed interest in

**Chapter-level changes** (surface explicitly):

- Drop the next chapter and replace it with a different topic
- Reorder upcoming chapters
- Split the next chapter into two
- Merge upcoming chapters

### 9.2 Apply silent adjustments directly

Edit the next chapter's stub file in place, updating only the "What the agent will research and explain when expanded" bullets and the concept list if needed. If the concept list changes, dispatch graph-mutator to update chapter assignments.

### 9.3 Surface chapter-level changes

If a chapter-level change is warranted, present it:

> Given that <concept> was shaky this chapter and you mentioned <interest>, I'd suggest we <specific change, e.g., drop chapter 4 on X in favor of working through Y next>. Sound good?

Wait for explicit approval. On approval, edit `outline.md`, dispatch graph-mutator for any concept reassignments, and update the affected stub files. On rejection, leave the curriculum unchanged.

### 9.4 Present the next chapter stub

Show the next chapter's (possibly adjusted) stub:

> Next up: chapter <N+1> — <Title>.
>
> <stub summary>
>
> I'll research and expand it when you're ready. Shall we continue, or call it for today?

## Step 10 — Loop or exit

- **Continue** — return to Step 1.4 with `current_chapter` incremented. The stub expansion runs, then Step 2 onward.
- **Exit** — persist `state.json` (already done in Step 8), say goodbye, tell the user "/tutor:study will pick up exactly here next time." Done.

## Error handling

- **State file corrupt**: back up `state.json` to `state.json.bak`, surface the problem, ask user how to proceed.
- **Chapter file corrupt**: try to recover by re-dispatching chapter-expander. If still broken, surface and stop.
- **graph-mutator failure**: surface the violation, ask user how to proceed. Do not silently ignore.
- **researcher failure during 1.4a**: retry once with a reformulated question. If still failing, surface and offer to continue with reduced research.
- **chapter-expander failure**: one targeted retry. If still failing, surface.

## Constraints

- **The briefing is pasted verbatim.** Never rewrite it.
- **Quiz questions are pasted verbatim.** Never rewrite.
- **Scaffolding sections are tutor-private.** Never read them verbatim to the user.
- **The must-cover checklist drives coverage.** Do not transition to the quiz until it's full.
- **Meta-analysis is mandatory.** Do not skip Step 7 even if the quiz score is perfect — interest signals still need capturing.
- **State persistence is mandatory at chapter boundaries.** Never advance to the next chapter with a half-saved state.
- **Graph mutations go through graph-mutator only.** Never write to `concepts.dot` directly from this skill.
- **`research/chapter-NN-research.md` is written by the main agent**, not by any subagent.
