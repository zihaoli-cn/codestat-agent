#!/bin/bash
set -e

# Environment variables:
# - REPO_URL: Repository clone URL
# - REPO_NAME: Repository full name
# - BRANCH: Branch name
# - COMMIT_SHA: Commit SHA
# - TASK_ID: Task identifier
# - CLOC_ARGS: Additional CLOC arguments
# - USE_GITIGNORE: Whether to use .gitignore (1 or 0)

REPO_DIR="/workspace/repo"
RESULT_FILE="/workspace/results/${TASK_ID}.json"

echo "=== CodeStat Worker ==="
echo "Repository: ${REPO_NAME}"
echo "Branch: ${BRANCH}"
echo "Commit: ${COMMIT_SHA}"
echo "Task ID: ${TASK_ID}"
echo ""

# Check if repository already exists
if [ -d "${REPO_DIR}/.git" ]; then
    echo "Repository exists, pulling latest changes..."
    cd "${REPO_DIR}"
    
    # Fetch and checkout
    git fetch origin "${BRANCH}"
    git checkout "${COMMIT_SHA}"
    
    echo "Repository updated to ${COMMIT_SHA}"
else
    echo "Cloning repository..."
    git clone --branch "${BRANCH}" "${REPO_URL}" "${REPO_DIR}"
    cd "${REPO_DIR}"
    git checkout "${COMMIT_SHA}"
    
    echo "Repository cloned successfully"
fi

echo ""
echo "=== Running CLOC ==="

# Build CLOC command
CLOC_CMD="cloc ."

# Add custom arguments
if [ -n "${CLOC_ARGS}" ]; then
    CLOC_CMD="${CLOC_CMD} ${CLOC_ARGS}"
else
    # Default to JSON output
    CLOC_CMD="${CLOC_CMD} --json"
fi

# Use git VCS mode to automatically respect .gitignore
# This is more reliable than manually parsing .gitignore
if [ "${USE_GITIGNORE}" = "1" ]; then
    echo "Using git VCS mode to respect .gitignore..."
    CLOC_CMD="${CLOC_CMD} --vcs=git"
else
    # If not using .gitignore, still use git mode but may include ignored files
    CLOC_CMD="${CLOC_CMD} --vcs=git --no-autogen"
fi

echo "Command: ${CLOC_CMD}"
echo ""

# Execute CLOC and save result
eval "${CLOC_CMD}" > "${RESULT_FILE}"

if [ $? -eq 0 ]; then
    echo ""
    echo "=== CLOC completed successfully ==="
    echo "Result saved to: ${RESULT_FILE}"
    
    # Show summary
    if command -v jq &> /dev/null && [ -f "${RESULT_FILE}" ]; then
        echo ""
        echo "Summary:"
        jq -r '.header | "Files: \(.n_files) | Lines: \(.n_lines) | Code: \(.n_lines - .n_comment - .n_blank)"' "${RESULT_FILE}" 2>/dev/null || true
    fi
    
    exit 0
else
    echo ""
    echo "=== CLOC failed ==="
    exit 1
fi
