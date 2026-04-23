---
name: second-opinion
description: Get an external AI review of plans, analysis, decisions, code, or any significant output using available CLI tools (claude, codex, gemini)
---

# Second Opinion

Get an independent AI review by spawning a separate CLI session. Use for ANY significant output: plans, research findings, analysis, recommendations, architecture, code, or strategic decisions.

## Workflow

### 1. Detect Available Reviewers

Run these checks to see what's available:

```bash
command -v claude && echo "claude: available" || echo "claude: not found"
command -v codex && echo "codex: available" || echo "codex: not found"
command -v gemini && echo "gemini: available" || echo "gemini: not found"
```

### 2. Prepare the Review Context

Gather the relevant context into a single prompt:
- **Architecture review**: Summarize the design, list files, describe trade-offs
- **Security audit**: Include the code under review, highlight trust boundaries
- **Code review**: Include the diff or file contents, describe intent

### 3. Run the Review

Use whichever CLIs are available. Prefer using multiple for diverse perspectives.

#### Model Selection

Pick the right model tier for the review type:

| Review Type | Codex Model | Reasoning | Gemini Model | Why |
|-------------|-------------|-----------|--------------|-----|
| Architecture / Security | `gpt-5.4` | `xhigh` | `gemini-2.5-pro` | Deep reasoning about trade-offs and attack surfaces |
| Code review / Correctness | `gpt-5.4` | `high` | `gemini-2.5-pro` | Thorough but doesn't need maximum compute |
| Business / Strategy | `gpt-5.4` | `xhigh` | `gemini-2.5-pro` | Non-engineering topics: mission, positioning, market analysis |

**Claude** (always available):
```bash
claude -p "You are a senior reviewer. Review the following for [architecture|security|correctness]. Be critical and specific. Context: <paste context>"
```

**Codex** (if installed):
```bash
# Architecture/security — gpt-5.4, max reasoning
codex exec -m gpt-5.4 -c model_reasoning_effort=xhigh "Review this code for [focus area]. Be critical: <paste context>"

# Code review — gpt-5.4, high reasoning
codex exec -m gpt-5.4 -c model_reasoning_effort=high "Review this code for [focus area]. Be critical: <paste context>"

# Business/strategy — gpt-5.4, max reasoning
codex exec -m gpt-5.4 -c model_reasoning_effort=xhigh "Review this for [focus area]. Be critical: <paste context>"
```

**Gemini** (if installed):
```bash
gemini -m gemini-2.5-pro -p "Review this design for [focus area]. Be specific about risks: <paste context>"
```

### 4. Synthesize Results

After collecting responses:
1. List areas where reviewers **agree** — these are high-confidence findings
2. List areas where reviewers **disagree** — these need human judgment
3. Highlight any **critical issues** (security, data loss, correctness)
4. Present a prioritized action list

## Review Types

| Type | Focus | Key Questions |
|------|-------|---------------|
| Plan       | Completeness, feasibility, gaps          | "What's missing? Are dependencies identified? Is scope realistic?" |
| Analysis   | Logic, bias, completeness                | "Are conclusions supported by evidence? What's overlooked? Any logical gaps?" |
| Strategy   | Market fit, risks, alternatives          | "What's the counter-argument? What assumptions are untested?" |
| Research   | Coverage, accuracy, sources              | "Is this comprehensive? Are sources reliable? What's missing from the picture?" |
| Architecture | Structure, scalability, maintainability | "Will this scale? Is it over-engineered? Are responsibilities clear?" |
| Security | Injection, auth, secrets, trust boundaries | "What can an attacker do? Where is input trusted? Are secrets exposed?" |
| Code | Correctness, edge cases, readability | "Does this handle errors? Are there race conditions? Is it testable?" |
| Decision | Trade-offs, alternatives, risks | "What are we giving up? What's the rollback plan? What are we not seeing?" |

## Tips

- Keep review prompts under 4000 words for best results
- Include file paths and line numbers for code reviews
- Ask for specific, actionable feedback — not general praise
- Run the same prompt through multiple models when possible for diversity
