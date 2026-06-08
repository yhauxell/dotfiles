---
name: ticket-refinement
description: Refine a raw ticket / user story from any tracker (Linear, Jira, ClickUp, GitHub Issues, GitLab Issues, Shortcut, or a raw idea) into engineering-ready requirements: Gherkin acceptance criteria, impacted areas, API/data impacts, edge cases. Use proactively whenever a ticket URL or `PROJ-123`-style key appears in the prompt, or when a story needs engineering-level clarification before architecture/design. The output is plain Markdown that pastes cleanly back into any tracker.
---

# Ticket refinement

Turn a raw ticket into engineering-ready requirements. Tracker-agnostic — works with input from Linear, Jira, ClickUp, GitHub/GitLab Issues, Shortcut, or a raw idea pasted in chat. Output is Markdown ready to paste back into the source tracker.

## When to use

- A ticket URL or `PROJ-123`-style key appears in the prompt.
- A user story is too vague for the architect to design against.
- `change_class = feature` or `epic` (per agent constitution §0).

**Skip when:** `change_class = trivial` (copy tweak, single-file refactor, dep bump). Refining a 2-line fix is bureaucracy.

## Operating constraints

- Output is Markdown suitable to paste into any ticket tracker.
- When you need codebase context, run an exploration pass (search, read) before drawing conclusions.
- Prefer concrete, testable statements over vague guidance.
- Identify the source tracker from the input (URL pattern or ticket key) and mirror its conventions where helpful (e.g. include the ticket key in the title) — but never hardcode tracker-specific terminology in the body.

## Procedure

1. Read the provided story / ticket / idea.
2. Analyze the relevant codebase via an exploration pass.
3. Define concrete acceptance criteria (prefer Gherkin syntax).
4. Identify impacted files, API/data changes, and edge cases.
5. Emit the refined description in Markdown.

## Output format

```markdown
### Refined story
- **Problem / context**
- **Goals**
- **Non-goals**
- **Assumptions**

### Acceptance criteria
<Gherkin scenarios>

### Technical requirements
- **UI/UX**
- **State management**
- **Analytics/telemetry (if applicable)**
- **Permissions / feature flags (if applicable)**

### API & data impacts
- **Endpoints/contracts impacted**
- **Backward compatibility considerations**
- **Error handling**

### Impacted code areas
<likely folders/files, best-effort from exploration>

### Edge cases
<bulleted list>
```

## Handoff

For `feature` and `epic` classes, the refined story feeds `frontend-architect` (which writes the SPEC). The refined Markdown is conversational context; the SPEC is the contract.
