# Tutor Plugin Manual Test Plan

Run through this checklist against a fresh Claude Code session with the tutor plugin enabled. Each check is pass/fail.

## Pre-flight

- [ ] Python 3.8+ installed and on PATH
- [ ] `pip install pydot networkx pytest` succeeds
- [ ] Graphviz CLI installed and `dot -V` prints a version (optional but recommended)
- [ ] The `c200v-marketplace` plugin source includes the `tutor/` directory
- [ ] `tutor/scripts/test_validate_concept_graph.py` passes with `pytest -v`

## Slice 1 — Scaffolding

- [ ] The plugin appears in Claude Code's plugin list after enabling
- [ ] `tutor/.claude-plugin/plugin.json` loads without error
- [ ] `.claude-plugin/marketplace.json` lists both `professional-twin` and `tutor`
- [ ] `tutor/README.md` is readable and describes the commands accurately

## Slice 2 — Agent definitions

- [ ] The Agent tool lists all five agent types (`researcher`, `graph-builder`, `graph-mutator`, `outline-builder`, `chapter-expander`) in its subagent_type dropdown, prefixed with `tutor:`
- [ ] Dispatching `researcher` with a synthetic question returns a structured findings block matching the return contract

## Slice 3 — `tutor:create` through outline

Test topic: "I want to know more about remote sensing, with a focus on military and nature conservation applications as well as a focus on satellites, specifically SAR."

- [ ] `/tutor:create` with the topic above runs the light-scan research step (parallel dispatches visible in the agent UI)
- [ ] The agent asks informed interview questions (not generic ones)
- [ ] Deep research runs in parallel after the interview
- [ ] `~/.claude/learning/<slug>/research/build-phase-summary.md` is written and readable
- [ ] `course.md` is written with learner profile and scope sections populated
- [ ] `concepts.dot` is generated, passes the validator, contains 30–80 nodes
- [ ] `concepts.png` is generated if Graphviz is installed
- [ ] The agent presents the graph to the user and accepts at least one modification via graph-mutator (try: "add ship detection as a concept")
- [ ] `outline.md` is generated with 6–20 chapters
- [ ] Stub chapter files exist in `chapters/` with status `stub`
- [ ] Validator passes with `--outline`
- [ ] `~/.claude/learning/index.json` is updated with the new course and `most_recent` is set

## Slice 4 — Chapter 1 expansion

- [ ] During `/tutor:create`, after outline approval, per-chapter research runs in parallel for chapter 1
- [ ] `research/chapter-01-research.md` is written
- [ ] `chapter-expander` is dispatched and returns a valid expanded chapter file
- [ ] The chapter file has `status: expanded`, a non-empty Briefing, a Must-Cover checklist, a Probing Bank (8–15 items), Common Misconceptions (4–8), Anticipated Tangents (2–5), and an End-of-Chapter Quiz (5–8 questions)
- [ ] `state.json` is initialized with chapter 1 `status: ready`
- [ ] The agent tells the user the course is ready and points to `/tutor:study`

## Slice 5 — `tutor:study` chapter 1 run

- [ ] `/tutor:study` with no argument loads the most recent course
- [ ] The briefing is pasted verbatim (compare first 200 chars against the chapter file)
- [ ] The agent transitions into dialogue with a probing question
- [ ] Dialogue feels like a conversation with an expert — not a script, not a list of questions
- [ ] When you chase a tangent, the agent follows and eventually steers back
- [ ] When the must-cover is full (simulate by engaging thoroughly with every concept), the agent transitions to the quiz
- [ ] Quiz questions are pasted verbatim one at a time
- [ ] Each answer gets a conversational evaluation, not a score
- [ ] The agent announces a final count + shaky concepts
- [ ] Meta-analysis runs: shaky concepts are classified
- [ ] `state.json` is updated: chapter 1 `status: completed`, quiz score recorded, shaky concepts logged
- [ ] `concepts.dot` is updated via graph-mutator: covered concepts marked `covered`, shaky ones marked `shaky`
- [ ] The agent proposes chapter 2 with any adaptations

## Slice 6 — Chapter 2 and 3

- [ ] Approving chapter 2 triggers expansion (per-chapter research in parallel, then chapter-expander)
- [ ] Chapter 2 runs through briefing → dialogue → quiz → meta-analysis → state update
- [ ] Chapter 3 runs through the full loop
- [ ] The three-chapter run completes without state corruption or validation failures

## Error handling checks

- [ ] Manually corrupt `concepts.dot` (delete a required attribute from one node) and run `/tutor:study`. The next graph-mutator dispatch should detect the corruption on its pre-edit read and refuse to proceed, OR the study skill should surface the issue.
- [ ] Delete `concepts.png` and run a graph-mutator dispatch. The image should be regenerated automatically.
- [ ] Make `~/.claude/learning/index.json` invalid JSON. The next `/tutor:study` should surface the error and not crash.

## v1 done

All checks above pass → v1 is done. File any failures as bugs to fix before declaring the plugin shippable.
