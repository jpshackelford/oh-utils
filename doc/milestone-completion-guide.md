# Milestone Completion Guide for OpenHands Utilities Refactoring

This document provides step-by-step instructions for completing each milestone in the architectural refactoring project. It ensures systematic progress with proper testing, quality checks, and task tracking.

## Overview

The refactoring project consists of 4 major milestones as defined in `doc/architectural-review.md`:

- **M1**: Consolidate API Client
- **M2**: Shared Command Infrastructure  
- **M3**: Improve Test Coverage
- **M4**: Documentation and Cleanup

Each milestone must be completed with:
- ✅ All automated tests passing
- ✅ All linting and type checking clean
- ✅ All pre-commit checks passing
- ✅ Manual testing completed for impacted functionality
- ✅ All milestone acceptance criteria met
- ✅ All task checklist items completed

## Prerequisites

Before starting any milestone work:

```bash
# Ensure development environment is set up
make dev-setup

# Verify current state is clean
make ci

# Check current test coverage
make test
```

## Step-by-Step Milestone Completion Process

### Phase 1: Pre-Work Verification

**Step 1.1: Verify Clean Starting State**
```bash
# Check git status
git status

# Run full CI pipeline
make ci

# Verify tests pass
make test

# Check current coverage (should be ~13%)
# Review coverage report in htmlcov/index.html
```

**Step 1.2: Initialize Task Tracking**

Use the task_tracker tool to set up milestone tasks:

```
I'm starting work on [MILESTONE_NAME]. Let me use the task tracker to organize the work items from the architectural review document.

[Use task_tracker tool to create tasks based on the milestone's checklist items from architectural-review.md]
```

**Step 1.3: Create Test Execution Document**

```bash
# Copy the test execution template
cp doc/test-plan/test-execution-checklist-template.md doc/test-plan/test-execution-$(date +%Y-%m-%d)-[milestone].md

# Fill in the header information:
# - Date: Current date
# - Tester: Your name
# - Environment: OS/Python/uv versions
# - API Key Type: Full/Limited permissions  
# - Branch: Current branch name
```

### Phase 2: Implementation Work

**Step 2.1: Begin Implementation**

For each task in the milestone:

1. **Update task status to "in_progress"** using task_tracker tool
2. **Implement the specific changes** according to the architectural review
3. **Write/update tests** following the testing rules in REPO.md:
   - Keep test methods short (≤15 lines, preferably 5-6)
   - Separate setup from assertions with blank line
   - One assertion per test (or closely related assertions)
   - Clear assertion messages for failures
   - Avoid complex mocking
4. **Run tests frequently** during development:
   ```bash
   # Run specific test file
   uv run pytest tests/test_[relevant_file].py -v
   
   # Run all tests
   make test
   ```

**Step 2.2: Continuous Quality Checks**

After each significant change:

```bash
# Check linting
make lint

# Check type checking  
make type-check

# Run full test suite
make test

# Check coverage improvement
# Review htmlcov/index.html
```

**Step 2.3: Task Completion**

When a task is complete:

1. **Verify the specific acceptance criteria** for that task
2. **Update task status to "done"** using task_tracker tool
3. **Commit the changes** with descriptive message:
   ```bash
   git add .
   git commit -m "feat: [description of change]
   
   - Implemented [specific functionality]
   - Added tests with [X]% coverage
   - Addresses task [task_id] in milestone [milestone_name]
   
   Co-authored-by: openhands <openhands@all-hands.dev>"
   ```

### Phase 3: Milestone Verification

**Step 3.1: Complete Automated Testing**

```bash
# Run full CI pipeline
make ci

# Verify all tests pass
make test

# Check coverage meets milestone targets
# M1: API client tests >90% coverage
# M2: Command infrastructure comprehensive coverage  
# M3: Overall coverage >80%
# M4: Maintain coverage levels
```

**Step 3.2: Manual Testing**

1. **Identify impacted functionality** based on changes made
2. **Run relevant manual tests** from the test execution document:
   ```bash
   # Example: If API client was changed, test:
   # - Server management commands (1.2.x)
   # - Conversation management commands (1.3.x)  
   # - Interactive mode (1.4)
   # - Error handling (1.5.x)
   ```
3. **Document test results** in the test execution document
4. **Address any failures** before proceeding

**Step 3.3: Milestone Acceptance Criteria Verification**

For each milestone, verify ALL acceptance criteria are met:

**M1 - Consolidate API Client:**
- [ ] All linting and type checking passes
- [ ] API client tests achieve >90% coverage
- [ ] Both CLI and interactive modes use the same API client
- [ ] Existing integration tests pass with consolidated API client
- [ ] No regression in fixture-based test coverage

**M2 - Shared Command Infrastructure:**
- [ ] Command boilerplate reduced by >80%
- [ ] Conversation ID resolution logic centralized
- [ ] All commands use consistent error handling
- [ ] New command infrastructure has comprehensive integration tests using existing fixtures

**M3 - Improve Test Coverage:**
- [ ] Overall test coverage >80%
- [ ] All CLI commands have integration tests
- [ ] Configuration management fully tested
- [ ] Fixture-based testing approach extended to all new functionality
- [ ] Sanitization scripts handle any new API endpoints

**M4 - Documentation and Cleanup:**
- [ ] Architecture documentation updated
- [ ] Code comments and docstrings improved
- [ ] Deprecated code removed

### Phase 4: Milestone Completion

**Step 4.1: Final Quality Gate**

```bash
# Run complete CI pipeline
make ci

# Verify pre-commit hooks pass
make pre-commit-install
git add . && git commit --amend --no-edit  # Trigger pre-commit hooks

# Run manual test suite for impacted areas
# Complete test execution document
```

**Step 4.2: Milestone Documentation**

1. **Update task tracker** - mark all tasks as "done"
2. **Complete test execution document** with:
   - All test results
   - Performance notes
   - Issues found (if any)
   - Recommendations
3. **Update architectural review document** - check off completed milestone items

**Step 4.3: Commit and Push**

```bash
# Final commit for milestone
git add .
git commit -m "feat: complete milestone [M#] - [milestone name]

- All acceptance criteria met
- Test coverage: [current %] (target: [target %])
- Manual testing completed
- All quality gates passed

Closes: [milestone tasks]

Co-authored-by: openhands <openhands@all-hands.dev>"

# Push to remote (only when explicitly requested)
# git push origin [branch-name]
```

## Quality Gates Summary

Each milestone must pass ALL of these gates:

### Automated Quality Gates
- [ ] `make ci` passes completely
- [ ] `make test` shows all tests passing
- [ ] Test coverage meets milestone targets
- [ ] `make lint` passes with no warnings
- [ ] `make type-check` passes with no errors
- [ ] Pre-commit hooks pass

### Manual Quality Gates  
- [ ] Manual testing completed for impacted functionality
- [ ] Test execution document completed
- [ ] All milestone acceptance criteria verified
- [ ] All task tracker items marked "done"

### Documentation Gates
- [ ] Code changes properly documented
- [ ] Test execution results documented
- [ ] Any issues or recommendations documented
- [ ] Architectural review checklist updated

## Troubleshooting

### Common Issues

**Tests failing after changes:**
1. Check if fixture compatibility is maintained
2. Verify API method signatures haven't changed
3. Review test setup and mocking
4. Check for import path changes

**Coverage not meeting targets:**
1. Identify uncovered code in htmlcov/index.html
2. Add focused unit tests for missed lines
3. Ensure tests exercise actual functionality, not just setup
4. Consider integration tests for complex workflows

**Type checking failures:**
1. Add proper type annotations
2. Update imports for moved/renamed modules
3. Check for missing py.typed markers in dependencies
4. Consider type: ignore comments for external library issues

**Manual tests failing:**
1. Verify environment setup is correct
2. Check API key permissions
3. Ensure server configuration is valid
4. Review test plan accuracy against current implementation

## Agent Prompting Guidelines

To ensure the agent uses this process effectively, use prompts like:

```
I'm ready to start milestone [M#]. Please:

1. Use the task_tracker tool to set up all tasks from the architectural review document
2. Verify the current state is clean (tests passing, linting clean)
3. Create a test execution document for this milestone
4. Begin implementation following the milestone completion guide
5. Update task status as work progresses
6. Run manual tests for any functionality impacted by changes
7. Verify all acceptance criteria before marking the milestone complete

Remember to follow the testing rules in REPO.md and ensure each commit has all quality gates passing.
```

This systematic approach ensures that each milestone is completed with high quality, comprehensive testing, and proper documentation while maintaining the valuable fixture-based testing infrastructure.