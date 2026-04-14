# tutor

A personal adaptive learning plugin for Claude Code. Create a custom course on any topic and study it through guided, expert-tutor-style sessions. The plugin is designed for a single learner — everything it produces is personalized to you, tuned to your background and goals.

## What it does

- **`/tutor:create "<topic prompt>"`** — Build a new personalized course on a topic. The plugin researches the topic, interviews you about your background and goals, builds a concept graph and curriculum outline, and generates the first chapter so you can start immediately.
- **`/tutor:study [course-slug]`** — Resume an existing course (or the most recently studied one). Walks you through one or more chapters in an expert-tutor style: a short briefing, then a guided dialogue, then a quiz, then an adaptive proposal for the next chapter.

Courses live under `~/.claude/learning/<course-slug>/` as plain markdown, JSON, and DOT files. Every course is yours, personal, and git-friendly.

## How it works

The plugin draws from Dan McCreary's intelligent-textbook work but scopes it down for personal use:

- **A concept graph** (`concepts.dot`) is the ground truth. Every concept in your course is a node; edges encode "A depends on B". The graph is validated after every change.
- **Chapters start as stubs and expand lazily.** When you start a new chapter in `/tutor:study`, the plugin runs focused web research, then generates a full lesson plan for that chapter. This makes adaptation cheap — upcoming chapters can shift emphasis based on how your earlier ones went.
- **Study sessions follow a fixed rhythm.** Briefing (~5 min of reading) → guided dialogue (the agent asks probing questions, follows your tangents, and tracks which concepts have landed) → end-of-chapter quiz → meta-analysis of shaky concepts → proposal for the next chapter.
- **Adaptation is built in.** Shaky concepts get reinforced in upcoming chapters. Interest signals you drop during dialogue get captured and honored. Chapter-level structural changes are always confirmed with you before they happen.

## Installation

The plugin is shipped through the `c200v-marketplace` — install the marketplace, then enable `tutor`.

## Dependencies

- Python 3.8+
- Python packages: `pydot`, `networkx` (install with `pip install pydot networkx`)
- Optional: Graphviz CLI (`dot` command) for rendering `concepts.png` images of your concept graph. Without Graphviz, everything still works — you just don't get the rendered images.

The plugin will check for these at first run and surface install instructions if anything is missing.

## Example

```
/tutor:create I want to know more about remote sensing, with a focus on military and nature conservation applications as well as a focus on satellites, specifically SAR.
```

The plugin will:

1. Run light web research to understand the topic.
2. Interview you with informed questions about your background, goals, and how deep you want to go.
3. Run deep research based on your answers.
4. Build a concept graph of ~30–80 concepts with prerequisite relationships.
5. Present the graph and a proposed outline of chapters for your review.
6. Generate the first chapter in full.
7. Hand off to `/tutor:study` to begin.

Subsequent sessions:

```
/tutor:study
```

Resumes the most recent course and walks you through the next chapter.

## Course folder layout

Each course lives in `~/.claude/learning/<slug>/`:

```
remote-sensing-sar/
├── course.md            ← title, your learner profile, scope, design rationale
├── concepts.dot         ← the concept graph (canonical)
├── concepts.png         ← rendered graph image (if Graphviz installed)
├── outline.md           ← chapter list with stubs
├── state.json           ← progress, quiz history, shaky concepts, interest signals
├── chapters/            ← stub and expanded chapter files
└── research/            ← consolidated research notes per phase/chapter
```

Everything is plain text. Run `git init` inside the course folder to get a full history of how the course evolved with you.

## License

MIT — see [LICENSE](LICENSE).
