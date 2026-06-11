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
- **The whole ticket is context, not just the description.** Comments, attachments, and embedded links routinely carry the real requirements (scope changes agreed in a comment thread, a screenshot that contradicts the description, the Figma link that defines the actual UI). When tracker tools are available, fetch comments and attachments — do not refine from the description alone.

## Procedure

1. Read the **full** ticket: description, **all comments** (newest decisions win over the original description — note when a comment supersedes it), attachments, and screenshots. Fetch them via the tracker's tools when available.
2. **Extract design sources**: collect every Figma URL found anywhere in the ticket (description, comments, attachment links) and every screenshot/mockup image. These feed `figma-design-implementer` downstream — capture them verbatim, with a note on where each was found and what it claims to show.
3. Analyze the relevant codebase via an exploration pass.
4. Define concrete acceptance criteria (prefer Gherkin syntax). Where a comment or screenshot resolved an ambiguity, bake the resolution into the AC rather than restating the ambiguity.
5. Identify impacted files, API/data changes, and edge cases.
6. Emit the refined description in Markdown, including the `Design sources` section whenever any were found.

## Output format

```markdown
### Refined story
- **Problem / context**
- **Goals**
- **Non-goals**
- **Assumptions**

### Design sources (feed figma-design-implementer)
<Omit this section entirely if none were found.>
- **Figma**: <URL> — found in <description | comment by X on DATE>; shows <frame/flow>
- **Screenshots/mockups**: <attachment name or URL> — <what it shows>
- **Comment-sourced decisions affecting the design**: <e.g. "comment 2026-05-02: empty state dropped from scope">

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

**When `Design sources` contains Figma URLs**, the pipeline routes through `figma-design-implementer` *before* the architect: invoke it with the extracted Figma URL(s) **plus** the relevant ticket context (the comment-sourced design decisions and what each screenshot shows), so it extracts design context with the same understanding of scope you have. Its `Design context` block and the refined story then go to `/architect` together. State this next step explicitly when emitting the refined story — don't leave the routing implicit.
