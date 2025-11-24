# Testing Release Process

This document explains how to test the release process on feature branches before merging to main.

## Overview

We now have two ways to test releases:

1. **Dedicated Test Release Workflow** (`test-release.yml`) - Designed specifically for testing
2. **Modified Main Release Workflow** (`release.yml`) - Now supports test mode

## Method 1: Using the Test Release Workflow

The `test-release.yml` workflow is designed specifically for testing releases on any branch.

### Features:

- ✅ Runs on any branch
- ✅ Creates test versions with branch name and timestamp
- ✅ Dry-run mode by default (no actual release created)
- ✅ Optional actual release creation (as draft + prerelease)
- ✅ Comprehensive logging and preview

### How to Use:

1. **Navigate to Actions tab** in GitHub
2. **Select "Test Release" workflow**
3. **Click "Run workflow"**
4. **Configure options:**
   - `version`: Optional custom version (e.g., "1.2.3-test")
   - `create_actual_release`: Set to `true` to create actual GitHub release
   - `branch_name`: Auto-detected, but can override

### Example Test Versions:

- Auto-generated: `v0.1.0-test-jps-ci-20241124-143022`
- Custom: `v1.2.3-test` (if you specify version)

## Method 2: Using Main Release Workflow in Test Mode

The main `release.yml` workflow now supports a test mode.

### How to Use:

1. **Navigate to Actions tab** in GitHub
2. **Select "Release" workflow**
3. **Click "Run workflow"**
4. **Configure options:**
   - `version`: Optional custom version
   - `test_mode`: Set to `true` for testing

### Test Mode Behavior:

- Creates draft + prerelease on GitHub
- Adds test suffix to version if not on main branch
- Includes test metadata in release notes
- Marks release clearly as test release

## What Gets Tested

Both workflows test the complete release process:

1. ✅ **Environment Setup**: uv, Python, dependencies
2. ✅ **Version Determination**: Auto-increment or custom
3. ✅ **Package Building**: Creates wheel and source distributions
4. ✅ **Changelog Generation**: From git commits
5. ✅ **GitHub Release Creation**: Tags, releases, artifacts
6. ✅ **PyPI Publishing Simulation**: Shows what would be published

## What Requires Main Branch

The following aspects of the release process are tied to the main branch:

### Automatic Triggers

- `workflow_run` trigger only works on main branch
- This is by design - automatic releases should only happen from main

### Production Releases

- Non-test releases should only be created from main branch
- This ensures release integrity and proper versioning

### What Works on Any Branch

- Manual workflow triggers (`workflow_dispatch`)
- Package building and testing
- Version determination
- Changelog generation
- Test release creation

## Testing Scenarios

### Scenario 1: Dry-Run Test (Recommended First)

```
Workflow: Test Release
Options:
  - create_actual_release: false (default)
  - version: (leave empty for auto-generation)
```

**Result**: Complete process simulation with detailed logging, no actual release

### Scenario 2: Draft Test Release

```
Workflow: Test Release
Options:
  - create_actual_release: true
  - version: (leave empty for auto-generation)
```

**Result**: Creates actual draft prerelease on GitHub

### Scenario 3: Test Mode with Main Workflow

```
Workflow: Release
Options:
  - test_mode: true
  - version: (optional)
```

**Result**: Creates draft prerelease using main workflow logic

## Cleanup

Test releases are created as:

- **Draft**: Won't appear in main releases list
- **Prerelease**: Clearly marked as test/beta
- **Deletable**: Can be safely deleted after testing

To clean up test releases:

1. Go to repository Releases page
2. Find draft/prerelease test releases
3. Delete them (this also removes the git tag)

## Troubleshooting

### Common Issues:

1. **Permission Errors**: Ensure workflow has `contents: write` permission
2. **Missing Dependencies**: Workflow installs all dependencies automatically
3. **Version Conflicts**: Test versions include timestamps to avoid conflicts
4. **Branch Protection**: Test workflows don't push to branches, only create releases

### Debugging:

1. **Check workflow logs** for detailed execution information
2. **Use dry-run mode first** to validate process without side effects
3. **Verify package contents** in workflow output
4. **Test with custom versions** to validate version handling

## Integration with CI

The test workflows are independent of CI requirements:

- Don't wait for CI completion (unlike main branch releases)
- Can run even if CI is failing (useful for testing fixes)
- Provide immediate feedback on release process

## Next Steps

After successful testing:

1. Merge PR to main branch
2. Automatic release will trigger after CI passes
3. Production release will be created with proper versioning

## Future Enhancements

Potential improvements for testing:

- Test PyPI publishing to test.pypi.org
- Integration testing of published packages
- Automated cleanup of old test releases
- Slack/email notifications for test releases
