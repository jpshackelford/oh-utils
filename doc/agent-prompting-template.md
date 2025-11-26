# Agent Prompting Template for Milestone Completion

Use these prompts to ensure the agent follows the systematic milestone completion process.

## Key Document References

Before starting, ensure the agent has access to these critical documents:

- **Architectural Review**: `doc/architectural-review.md` - Contains all milestone definitions, acceptance criteria, and implementation checklists
- **Milestone Completion Guide**: `doc/milestone-completion-guide.md` - Step-by-step process for completing milestones
- **Testing Rules**: `.openhands/microagents/repo.md` - Repository guidelines and testing standards
- **Manual Test Plan**: `doc/test-plan/manual-test-plan.md` - Comprehensive manual testing procedures
- **Test Execution Template**: `doc/test-plan/test-execution-checklist-template.md` - Template for documenting test results
- **Agent Prompting Guide**: `doc/agent-prompting-template.md` - This document with example prompts

## Starting a Milestone

```
I'm ready to start milestone [M1/M2/M3/M4] from the architectural review. Please read and reference these key documents:

- doc/architectural-review.md (milestone definitions and acceptance criteria)
- doc/milestone-completion-guide.md (step-by-step process)
- .openhands/microagents/repo.md (testing rules and guidelines)
- doc/test-plan/manual-test-plan.md (manual testing procedures)

Then:

1. Use the task_tracker tool to set up all tasks from doc/architectural-review.md for this milestone
2. Verify the current state is clean by running:
   - make ci (all tests, linting, type checking)
   - Check current test coverage
3. Create a test execution document by copying doc/test-plan/test-execution-checklist-template.md to doc/test-plan/test-execution-$(date +%Y-%m-%d)-[milestone].md
4. Begin implementation following doc/milestone-completion-guide.md
5. Update task status as work progresses using the task_tracker tool
6. Run manual tests for any functionality impacted by changes using doc/test-plan/manual-test-plan.md
7. Verify all acceptance criteria from doc/architectural-review.md before marking the milestone complete

Remember to follow the testing rules in .openhands/microagents/repo.md and ensure each commit has all quality gates passing.
```

## During Implementation

```
Please continue working on the current milestone tasks. Reference these documents as needed:

- doc/architectural-review.md (specific implementation details for each task)
- .openhands/microagents/repo.md (testing rules and quality standards)
- doc/milestone-completion-guide.md (quality gate requirements)

For each task:

1. Update the task status to "in_progress" using task_tracker
2. Implement the changes according to doc/architectural-review.md
3. Write tests following the testing rules in .openhands/microagents/repo.md (short methods, clear assertions, minimal mocking)
4. Run tests frequently: make test
5. Check linting and type checking: make lint && make type-check
6. When complete, update task status to "done" and commit with descriptive message
7. Include "Co-authored-by: openhands <openhands@all-hands.dev>" in commit messages

Focus on one task at a time and ensure quality gates pass before moving to the next task.
```

## Before Milestone Completion

```
Before marking this milestone complete, please verify against these documents:

- doc/architectural-review.md (milestone acceptance criteria)
- doc/milestone-completion-guide.md (quality gate requirements)
- doc/test-plan/test-execution-[date]-[milestone].md (manual test results)

Verification checklist:

1. All task_tracker items are marked "done"
2. All milestone acceptance criteria from doc/architectural-review.md are met
3. Run complete quality gate checks per doc/milestone-completion-guide.md:
   - make ci passes completely
   - Test coverage meets milestone targets
   - All linting and type checking clean
4. Complete manual testing for impacted functionality using doc/test-plan/manual-test-plan.md
5. Document results in the test execution document
6. Document any issues found and ensure they're resolved
7. Make final commit with milestone completion message

Only mark the milestone complete when ALL quality gates pass.
```

## Quality Gate Verification

```
Please run the complete quality gate verification using these references:

- doc/milestone-completion-guide.md (complete quality gate checklist)
- doc/test-plan/manual-test-plan.md (manual testing procedures)
- doc/architectural-review.md (milestone acceptance criteria)

Quality gate checks:

1. Automated checks:
   - make ci (must pass completely)
   - make test (verify coverage targets from doc/architectural-review.md)
   - make lint (no warnings)
   - make type-check (no errors)

2. Manual testing:
   - Run manual tests from doc/test-plan/manual-test-plan.md for functionality impacted by this milestone
   - Complete the test execution document doc/test-plan/test-execution-[date]-[milestone].md
   - Document any issues found

3. Documentation:
   - Update task_tracker with all tasks marked "done"
   - Check off completed items in doc/architectural-review.md
   - Ensure test execution document is complete

Report the results of each check before proceeding.
```

## Troubleshooting

```
I'm encountering [specific issue] during milestone work. Please reference these documents for guidance:

- doc/milestone-completion-guide.md (troubleshooting section)
- .openhands/microagents/repo.md (testing rules and quality standards)
- doc/architectural-review.md (fixture-based testing approach)

Then:

1. Analyze the issue and identify potential root causes
2. Check if this relates to:
   - Fixture compatibility (for API changes) - see doc/architectural-review.md section 4.5
   - Test setup or mocking issues - see .openhands/microagents/repo.md testing rules
   - Import path changes
   - Type annotation problems
3. Propose 2-3 different approaches to resolve the issue
4. Implement the most appropriate solution
5. Verify the fix doesn't break other functionality
6. Update tests if needed to prevent regression

Follow the testing rules in .openhands/microagents/repo.md and ensure the solution maintains code quality.
```

## Example Complete Milestone Prompt

```
I'm ready to complete milestone M1 (Consolidate API Client) from the architectural review. Please read these key documents first:

- doc/architectural-review.md (M1 definition, tasks, and acceptance criteria)
- doc/milestone-completion-guide.md (systematic completion process)
- .openhands/microagents/repo.md (testing rules and quality standards)
- doc/test-plan/manual-test-plan.md (manual testing procedures)

Then:

1. Use task_tracker to organize all M1 tasks from doc/architectural-review.md:
   - Unified API Client (ohc/api.py enhancement)
   - Integration Test Preservation (verify fixtures work)
   - Remove Duplicate API Client (from conversation_manager)

2. Verify starting state: make ci should pass, current coverage ~13%

3. Create test execution document: doc/test-plan/test-execution-2025-11-26-m1.md

4. Implement each task following doc/milestone-completion-guide.md:
   - Update task status to "in_progress" before starting
   - Write tests following .openhands/microagents/repo.md testing rules
   - Run make test frequently
   - Mark "done" when complete with descriptive commit

5. Verify M1 acceptance criteria from doc/architectural-review.md:
   - All linting and type checking passes ✓
   - API client tests achieve >90% coverage ✓
   - Both CLI and interactive modes use same API client ✓
   - Existing integration tests pass with consolidated API ✓
   - No regression in fixture-based test coverage ✓

6. Complete manual testing using doc/test-plan/manual-test-plan.md for impacted functionality (server management, conversation commands, interactive mode)

7. Final quality gate per doc/milestone-completion-guide.md: make ci, manual tests complete, all tasks "done"

Follow the systematic process and ensure each commit has all quality gates passing.
```

## Key Reminders for Agents

- **Always reference key documents** before starting work:
  - `doc/architectural-review.md` for milestone definitions
  - `doc/milestone-completion-guide.md` for systematic process
  - `.openhands/microagents/repo.md` for testing rules
  - `doc/test-plan/manual-test-plan.md` for manual testing
- **Always use task_tracker** for milestone organization and progress tracking
- **Update task status** as work progresses (todo → in_progress → done)
- **Follow testing rules** in `.openhands/microagents/repo.md`
- **Run quality checks frequently** during development
- **Complete manual testing** for impacted functionality using `doc/test-plan/manual-test-plan.md`
- **Verify acceptance criteria** from `doc/architectural-review.md` before marking milestones complete
- **Document everything** in test execution documents
- **One task at a time** - maintain focus and quality
