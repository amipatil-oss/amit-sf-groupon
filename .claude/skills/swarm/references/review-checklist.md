# 6-Point Review Gate

Run this checklist before creating a PR for any phase. All items must pass.

## 1. File Inventory

- [ ] All files mentioned in the phase plan exist
- [ ] No unexpected files were created or modified
- [ ] Deleted files are intentionally removed

**How to check:**
```bash
git diff --name-only main...HEAD
```
Compare against the plan's expected file list.

## 2. Acceptance Criteria

- [ ] Every acceptance criterion from the phase plan is met
- [ ] Edge cases identified in the plan are handled
- [ ] No acceptance criteria were silently skipped

**How to check:** Review each criterion from the plan and verify with code/tests.

## 3. Tests

- [ ] New tests exist for new functionality
- [ ] All tests pass (not just new ones)
- [ ] No tests were disabled or skipped to make things pass

**How to check:**
```bash
# Run the project's test suite
npm test  # or pytest, cargo test, etc.
```

## 4. Integration

- [ ] No regressions in existing functionality
- [ ] API contracts are preserved (or intentionally changed)
- [ ] Database migrations are reversible (if applicable)

**How to check:**
```bash
# Run full test suite, not just unit tests
npm run test:integration  # or equivalent
```

## 5. Code Quality

- [ ] No TODO/FIXME/HACK comments left behind
- [ ] No commented-out code
- [ ] No hardcoded secrets, URLs, or credentials
- [ ] Consistent with project's existing patterns

**How to check:**
```bash
grep -rn "TODO\|FIXME\|HACK" --include="*.{ts,js,py,rs}" .
grep -rn "password\|secret\|api_key" --include="*.{ts,js,py,rs}" .
```

## 6. Documentation

- [ ] README updated if public API changed
- [ ] Inline comments for non-obvious logic
- [ ] Migration guide if breaking changes exist

**How to check:** Review changed files for public-facing changes.

---

## Retry Protocol

If any check fails:
1. Note which check(s) failed and why
2. Fix the issue
3. Re-run all 6 checks (not just the failed one)
4. Maximum 3 retry attempts per phase
5. After 3 failures: **STOP and escalate to human**
