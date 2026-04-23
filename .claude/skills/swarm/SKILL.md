---
name: swarm
description: Phased workflow orchestration. For code: git branches, PRs, review gates. For analysis/documents: structured phases with review checkpoints.
---

# Swarm — Phased Workflow Orchestration

Orchestrate multi-phase work with structured review gates between phases. Works for both code (git branches, PRs) and analytical/document work (phased outputs with second-opinion checkpoints).

## When to Use

- Executing a multi-phase plan from `tasks/todo.md` or a plan file
- Any work with 3+ distinct phases that benefit from review gates between them
- Multi-phase analytical work (research → analysis → recommendations → deliverable)
- Code implementations that benefit from separate PRs per phase

## Workflow Mode Selection

Determine the workflow mode based on the work type:
- **Code work** → Git workflow (branches, PRs, review gates)
- **Analytical/document work** → File workflow (phased outputs, second-opinion gates)

---

## A. Analytical/Document Workflow

### 1. Load the Plan

Read the phased plan. Identify each phase and its deliverables.

### 2. Execute Each Phase

For each phase:
1. Execute the phase (research, analysis, writing, etc.)
2. Write output to the project folder or `docs/`
3. Run **second-opinion gate** on the output
4. If gate raises critical issues: revise and re-review (max 3 attempts)
5. If gate passes: mark phase complete, move to next
6. If 3 retries exhausted: **stop and escalate to human**

### 3. Review Gate (Analytical)

| Check | Question |
|-------|----------|
| Completeness | Does the output cover all required areas? |
| Evidence | Are conclusions supported by data/sources? |
| Perspective | Are stakeholder viewpoints addressed? |
| Gaps | What's missing or overlooked? |
| Clarity | Is the output clear, structured, and actionable? |
| Accuracy | Are facts, numbers, and references correct? |

### 4. Human Escalation

Stop and ask the human when:
- Review gate fails 3 times on the same issue
- A phase requires decisions or context not in the plan
- New information fundamentally changes prior phase conclusions

---

## B. Code Workflow

### 1. Load the Plan

Read the phased plan from the source specified by the user (default: `tasks/todo.md`).
Identify each phase and its acceptance criteria.

### 2. Branch Strategy

For each phase:
```bash
git checkout main && git pull
git checkout -b phase-N/short-description
```

Naming: `phase-1/setup`, `phase-2/core-logic`, `phase-3/tests`, etc.

### 3. Execute Each Phase

For each phase:
1. Create the branch
2. Implement the phase (use superpowers agents for parallel work within a phase)
3. Run the **6-Point Review Gate** (see `references/review-checklist.md`)
4. If gate fails: fix and retry (max 3 attempts)
5. If gate passes: commit, push, create PR
6. If 3 retries exhausted: **stop and escalate to human**

### 4. Create PR per Phase

```bash
gh pr create --title "Phase N: Description" --body "$(cat <<'EOF'
## Phase N: Description

### Changes
- [list of changes]

### Review Gate Results
- [x] File inventory matches plan
- [x] Acceptance criteria met
- [x] Tests pass
- [x] No integration regressions
- [x] Code quality check
- [x] Docs updated (if needed)

### Phase Plan Reference
[Link to plan section]
EOF
)"
```

### 5. Human Escalation

Stop and ask the human when:
- Review gate fails 3 times on the same issue
- A phase requires architectural decisions not covered in the plan
- Tests reveal issues in previously merged phases
- Merge conflicts that aren't straightforward

## Configuration

The plan source can be:
- `tasks/todo.md` (default)
- Any markdown file with phased structure
- User-specified at invocation time

Phases are detected by headers like `## Phase 1:`, `### Step 1:`, or numbered lists.

## Tips

- Keep phases small — each should be a reviewable, mergeable unit
- Run the full test suite after each phase, not just new tests
- Use `git stash` to save WIP if you need to check another branch
- If a phase depends on a previous PR being merged, wait or stack on the branch
