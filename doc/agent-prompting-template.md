# Agent Prompting Template for Milestone Completion

Use these prompts to ensure the agent follows the systematic milestone completion process.

## Starting a Milestone

```
I'm ready to start milestone [M1/M2/M3/M4] from the architectural review document. Please:

1. Use the task_tracker tool to set up all tasks from the architectural review document for this milestone
2. Verify the current state is clean by running:
   - make ci (all tests, linting, type checking)
   - Check current test coverage
3. Create a test execution document by copying doc/test-plan/test-execution-checklist-template.md to doc/test-plan/test-execution-$(date +%Y-%m-%d)-[milestone].md
4. Begin implementation following the milestone completion guide in doc/milestone-completion-guide.md
5. Update task status as work progresses using the task_tracker tool
6. Run manual tests for any functionality impacted by changes
7. Verify all acceptance criteria before marking the milestone complete

Remember to follow the testing rules in .openhands/microagents/repo.md and ensure each commit has all quality gates passing.
```

## During Implementation

```
Please continue working on the current milestone tasks. For each task:

1. Update the task status to "in_progress" using task_tracker
2. Implement the changes according to the architectural review
3. Write tests following the testing rules (short methods, clear assertions, minimal mocking)
4. Run tests frequently: make test
5. Check linting and type checking: make lint && make type-check
6. When complete, update task status to "done" and commit with descriptive message
7. Include "Co-authored-by: openhands <openhands@all-hands.dev>" in commit messages

Focus on one task at a time and ensure quality gates pass before moving to the next task.
```

## Before Milestone Completion

```
Before marking this milestone complete, please verify:

1. All task_tracker items are marked "done"
2. All milestone acceptance criteria are met (check architectural-review.md)
3. Run complete quality gate checks:
   - make ci passes completely
   - Test coverage meets milestone targets
   - All linting and type checking clean
4. Complete manual testing for impacted functionality using the test execution document
5. Document any issues found and ensure they're resolved
6. Make final commit with milestone completion message

Only mark the milestone complete when ALL quality gates pass.
```

## Quality Gate Verification

```
Please run the complete quality gate verification:

1. Automated checks:
   - make ci (must pass completely)
   - make test (verify coverage targets met)
   - make lint (no warnings)
   - make type-check (no errors)

2. Manual testing:
   - Run manual tests for functionality impacted by this milestone
   - Complete the test execution document
   - Document any issues found

3. Documentation:
   - Update task_tracker with all tasks marked "done"
   - Check off completed items in architectural-review.md
   - Ensure test execution document is complete

Report the results of each check before proceeding.
```

## Troubleshooting

```
I'm encountering [specific issue] during milestone work. Please:

1. Analyze the issue and identify potential root causes
2. Check if this relates to:
   - Fixture compatibility (for API changes)
   - Test setup or mocking issues
   - Import path changes
   - Type annotation problems
3. Propose 2-3 different approaches to resolve the issue
4. Implement the most appropriate solution
5. Verify the fix doesn't break other functionality
6. Update tests if needed to prevent regression

Follow the testing rules and ensure the solution maintains code quality.
```

## Example Complete Milestone Prompt

```
I'm ready to complete milestone M1 (Consolidate API Client) from the architectural review. Please:

1. Use task_tracker to organize all M1 tasks:
   - Unified API Client (ohc/api.py enhancement)
   - Integration Test Preservation (verify fixtures work)
   - Remove Duplicate API Client (from conversation_manager)

2. Verify starting state: make ci should pass, current coverage ~13%

3. Create test execution document: doc/test-plan/test-execution-2025-11-26-m1.md

4. Implement each task following the milestone completion guide:
   - Update task status to "in_progress" before starting
   - Write tests following repo testing rules
   - Run make test frequently
   - Mark "done" when complete with descriptive commit

5. Verify M1 acceptance criteria:
   - All linting and type checking passes ✓
   - API client tests achieve >90% coverage ✓
   - Both CLI and interactive modes use same API client ✓
   - Existing integration tests pass with consolidated API ✓
   - No regression in fixture-based test coverage ✓

6. Complete manual testing for impacted functionality (server management, conversation commands, interactive mode)

7. Final quality gate: make ci, manual tests complete, all tasks "done"

Follow the systematic process and ensure each commit has all quality gates passing.
```

## Key Reminders for Agents

- **Always use task_tracker** for milestone organization and progress tracking
- **Update task status** as work progresses (todo → in_progress → done)
- **Follow testing rules** in .openhands/microagents/repo.md
- **Run quality checks frequently** during development
- **Complete manual testing** for impacted functionality
- **Verify acceptance criteria** before marking milestones complete
- **Document everything** in test execution documents
- **One task at a time** - maintain focus and quality