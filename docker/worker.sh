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

# Handle .gitignore
if [ "${USE_GITIGNORE}" = "1" ] && [ -f ".gitignore" ]; then
    echo "Using .gitignore for exclusions..."
    
    # Convert .gitignore to CLOC exclude list
    EXCLUDE_LIST="/tmp/cloc_exclude.txt"
    
    # Extract directory and file patterns from .gitignore
    grep -v '^#' .gitignore | grep -v '^$' | while read -r pattern; do
        # Remove leading/trailing slashes and wildcards for CLOC
        pattern=$(echo "$pattern" | sed 's:^/::' | sed 's:/$::')
        echo "$pattern"
    done > "${EXCLUDE_LIST}"
    
    if [ -s "${EXCLUDE_LIST}" ]; then
        CLOC_CMD="${CLOC_CMD} --exclude-list-file=${EXCLUDE_LIST}"
    fi
fi

# Add VCS mode to respect git
CLOC_CMD="${CLOC_CMD} --vcs=git"

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
