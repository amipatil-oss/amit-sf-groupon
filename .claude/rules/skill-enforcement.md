# Skill Enforcement

Before acting on ANY user request, match it against the entry gates table below.
If a match exists, invoke the skill BEFORE any other action — including clarifying questions.

## Entry Gates — invoke skill before acting

| User intent signals | Required skill | Why |
|---|---|---|
| "build", "add", "create feature", "implement", design work | brainstorming | Explore intent before building |
| "fix", "bug", "broken", "not working", "error", test failure | systematic-debugging | Diagnose before patching |
| "plan", multi-step task, 3+ changes needed | writing-plans | Plan before executing |
| Writing for Dusan's voice, newsletter, email to employees | ceo-voice | Match authentic tone |
| Architecture decision, system design, Groupon infra | groupon-enterprise-architect | Use domain knowledge |
| New project setup | new-project | Consistent scaffolding |
| Starting a session in CoS root | cos-welcome | Orientation first |

## Exit Gates — invoke proactively after producing output

| When | Required skill | Why |
|---|---|---|
| After completing ANY plan, analysis, research, design, or recommendation | second-opinion | External validation before presenting to user |
| After completing ANY non-trivial implementation task | ralph-loop | Iterative refinement catches what first pass misses |
| Before claiming work is "done" or "complete" | verification-before-completion | Evidence before assertions |

## Self-Check

Before any Write or Edit tool call, ask yourself:
- Did I invoke the relevant entry gate skill for this task type?
- If not, invoke it NOW before proceeding.

After producing significant output, ask yourself:
- Did I run second-opinion on this?
- Did I run ralph-loop if this was implementation work?
- If not, do it NOW before presenting to the user.

This is not optional. Skipping a skill to "save time" is a bug, not an optimization.
