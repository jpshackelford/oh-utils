# Release Workflow Guide

## Overview

The release workflow has been updated to resolve permission issues and ensure proper dependency management between CI and release processes.

## Key Changes Made

### 1. **Fixed Permission Issues**
- **Problem**: The release workflow was failing with "Permission denied" errors when trying to push back to the repository
- **Solution**: Removed git push operations that required special permissions
- **Result**: Releases now create GitHub releases and tags without modifying the repository directly

### 2. **Added Workflow Dependencies**
- **Problem**: Release workflow was running in parallel with CI instead of waiting for successful build/test completion
- **Solution**: Changed trigger from `push` to `workflow_run` that waits for CI completion
- **Result**: Releases only happen after successful CI builds

### 3. **Modernized Actions**
- Updated from deprecated `actions/create-release@v1` to `softprops/action-gh-release@v1`
- Added proper permissions declarations
- Improved error handling and logging

## How Releases Work Now

### Automatic Releases
1. **Trigger**: When code is pushed to `main` branch
2. **Dependency**: Waits for CI workflow to complete successfully
3. **Condition**: Only creates release if conventional commits are found since last tag
4. **Process**:
   - Checks for conventional commits (feat:, fix:, perf:, BREAKING CHANGE)
   - Determines new version by incrementing patch version
   - Builds package with `uv build`
   - Generates changelog from git commits
   - Creates GitHub release with tag and built artifacts

### Manual Releases
1. **Trigger**: Go to Actions → Release → Run workflow
2. **Options**: 
   - Can specify custom version (e.g., "1.2.3")
   - If no version specified, auto-increments patch version
3. **Process**: Same as automatic, but bypasses conventional commit check

## Version Management

Currently using simple patch version increment. For more sophisticated versioning:

1. **Semantic Versioning**: Consider implementing proper semantic version detection based on commit types:
   - `feat:` → minor version bump
   - `fix:` → patch version bump  
   - `BREAKING CHANGE:` → major version bump

2. **Manual Version Control**: Use the manual release trigger with specific version numbers

## Troubleshooting

### If Releases Still Fail
1. **Check CI Status**: Ensure CI workflow completed successfully
2. **Check Permissions**: Verify repository has proper GitHub Actions permissions
3. **Check Conventional Commits**: Ensure commits follow conventional format for automatic releases

### Permission Issues
The workflow now uses minimal permissions and doesn't push back to the repository, which should resolve most permission issues. If problems persist:

1. Check repository Settings → Actions → General → Workflow permissions
2. Ensure "Read and write permissions" is enabled for GITHUB_TOKEN
3. Consider using a Personal Access Token if needed (stored in repository secrets)

## Future Improvements

1. **Commitizen Integration**: Could re-enable commitizen for more sophisticated changelog generation
2. **PyPI Publishing**: Currently placeholder - can be enabled when ready to publish packages
3. **Release Notes**: Could enhance with PR links, contributor mentions, etc.
4. **Version Validation**: Add checks to prevent duplicate releases or invalid version formats

## Testing the Workflow

To test the release workflow:

1. **Manual Test**: Use the workflow_dispatch trigger in GitHub Actions
2. **Automatic Test**: Push conventional commits to main after CI passes
3. **Dry Run**: Check the workflow logs to see what version would be created

The workflow is now more robust and should handle the permission and dependency issues that were previously causing failures.