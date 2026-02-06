#!/bin/bash
set -euo pipefail

# openclaw_spec_execute.sh
# Orchestrates the Spec-Kit build flow driven by OpenClaw Dispatcher logic.

# Usage:
# ./openclaw_spec_execute.sh <LOCKED_JSON_PATH> <RUN_DIR>

LOCKED_JSON="$1"
RUN_DIR="$2"
WORK_ROOT="${3:-/data/janagi-builds}"

# Load configs from JSON using python (reliable parsing)
eval $(python3 -c "
import json, sys
data = json.load(open('$LOCKED_JSON'))
repo = data.get('repo', {})
print(f\"APP_NAME={repo.get('name', 'unnamed-app')}\")
print(f\"VISIBILITY={repo.get('visibility', 'private')}\")
print(f\"OWNER={repo.get('owner', '')}\")
print(f\"PRIMARY={data.get('primary_mode', 'both')}\")
print(f\"TEMPLATE={data.get('template', 'fastapi')}\")
print(f\"INTENT='{data.get('project_intent', '').replace(\"'\", \"'\\''\")}'\")
")

# Define Log Files (must match n8n expectation)
LOG_OC="$RUN_DIR/openclaw.log"
LOG_GEM="$RUN_DIR/gemini.log"
LOG_COP="$RUN_DIR/copilot.log"

log() {
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] $1" | tee -a "$LOG_OC"
}

log "Starting Execution for $APP_NAME ($TEMPLATE)"
log "Work Root: $WORK_ROOT"

# 1. Prepare Workspace
APP_DIR="$WORK_ROOT/$APP_NAME"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# 2. Git/Repo Setup
if [ ! -d ".git" ]; then
    log "Initializing new git repository..."
    git init
    git branch -M main
    
    # Try creating remote if OWNER is set and gh is available
    if command -v gh &> /dev/null && [ -n "$OWNER" ]; then
        if gh repo view "$OWNER/$APP_NAME" &>/dev/null; then
            log "Repo $OWNER/$APP_NAME already exists."
        else
            log "Creating GitHub repository $OWNER/$APP_NAME..."
            gh repo create "$OWNER/$APP_NAME" --"$VISIBILITY" --source=. --push || log "Warning: Failed to create remote repo."
        fi
    fi
else
    log "Using existing git repository."
fi

# 3. Spec Kit Bootstrap
log "Bootstrapping Spec Kit..."
git checkout -b base/spec-kit 2>/dev/null || git checkout base/spec-kit

if [ ! -f "speckit.yaml" ] && [ ! -f ".speckit/config.yaml" ]; then
    # Assuming 'specify' is installed via uv tool or in path
    if command -v specify &> /dev/null; then
        specify init --here --ai gemini || true
        git add .
        git commit -m "chore: initialize spec-kit" || true
    else
        log "ERROR: 'specify' CLI not found. Skipping init."
    fi
else
    log "Spec Kit already initialized."
fi

# 4. Agent Execution Function
run_agent() {
    local AGENT_NAME="$1"
    local BRANCH_NAME="impl/$AGENT_NAME"
    local LOG_FILE="$2"
    local PROFILE="$3" # e.g., google:default or github:copilot

    log "Preparing branch $BRANCH_NAME..."
    git checkout base/spec-kit
    git branch -D "$BRANCH_NAME" 2>/dev/null || true
    git checkout -b "$BRANCH_NAME"

    log "Invoking $AGENT_NAME Agent..."
    echo "--- Agent $AGENT_NAME Start ---" >> "$LOG_FILE"
    
    # Construct the instruction for the agent
    local INSTRUCTION="You are the CLI Implementer ($AGENT_NAME).
    CONTEXT:
    - App: $APP_NAME
    - Stack: $TEMPLATE
    - Intent: $INTENT
    
    MISSION:
    Follow the Spec Kit flow strictly:
    1. /speckit.constitution (Create constitution)
    2. /speckit.specify (Create specification)
    3. /speckit.plan (Create plan)
    4. /speckit.tasks (Create tasks)
    5. /speckit.implement (Write code & tests)
    
    REQUIREMENTS:
    - Commit after each phase.
    - Run tests often.
    - FINAL STATE: All tests passing.
    "

    # Execute OpenClaw Agent
    # We use 'timeout' to prevent infinite loops
    if command -v openclaw &> /dev/null; then
        timeout 600s openclaw agent --local \
            --profile "$PROFILE" \
            --session-id "${APP_NAME}-${AGENT_NAME}-build" \
            --message "$INSTRUCTION" \
            >> "$LOG_FILE" 2>&1 || echo "Agent finished or timed out" >> "$LOG_FILE"
    else
        echo "Mocking execution for $AGENT_NAME (openclaw CLI not found)" >> "$LOG_FILE"
        echo "Would run profile: $PROFILE" >> "$LOG_FILE"
        # Mock file creation for testing flow
        mkdir -p src
        echo "print('Hello from $AGENT_NAME')" > src/main.py
        git add .
        git commit -m "feat: mock implementation by $AGENT_NAME"
    fi
    
    echo "--- Agent $AGENT_NAME End ---" >> "$LOG_FILE"
}

# 5. Run Selected Implementers
if [[ "$PRIMARY" == "both" || "$PRIMARY" == "gemini" ]]; then
    run_agent "gemini" "$LOG_GEM" "${OPENCLAW_PROFILE_GEMINI:-google:default}"
fi

if [[ "$PRIMARY" == "both" || "$PRIMARY" == "copilot" ]]; then
    run_agent "copilot" "$LOG_COP" "${OPENCLAW_PROFILE_COPILOT:-github:copilot}"
fi

# 6. Evaluation & Winner Selection
log "Evaluating results..."
WINNER=""
G_SCORE=0
C_SCORE=0

check_score() {
    local BR="$1"
    git checkout "$BR" &>/dev/null || return 0
    local SCORE=0
    # Simple heuristic: Existence of code + Passing Tests
    if [ -f "pyproject.toml" ] || [ -f "package.json" ]; then SCORE=$((SCORE+1)); fi
    if command -v pytest &>/dev/null && pytest -q &>/dev/null; then SCORE=$((SCORE+2)); fi
    echo $SCORE
}

if [[ "$PRIMARY" == "both" ]]; then
    G_SCORE=$(check_score "impl/gemini")
    C_SCORE=$(check_score "impl/copilot")
    
    if [ "$C_SCORE" -gt "$G_SCORE" ]; then
        WINNER="impl/copilot"
    else
        WINNER="impl/gemini" # Default to gemini if tie or win
    fi
elif [[ "$PRIMARY" == "copilot" ]]; then
    WINNER="impl/copilot"
else
    WINNER="impl/gemini"
fi

log "Winner selected: $WINNER"

# 7. Create PR
log "Creating Pull Request..."
git checkout "$WINNER"
git push -u origin "$WINNER" 2>/dev/null || true

# Ensure main exists
if ! git show-ref --verify --quiet refs/heads/main; then
    git branch main base/spec-kit
    git push -u origin main 2>/dev/null || true
fi

PR_URL=""
if command -v gh &> /dev/null; then
    PR_URL=$(gh pr create --base main --head "$WINNER" --title "feat: SpecKit Implementation ($APP_NAME)" --body "Automated build by OpenClaw ($WINNER)" 2>/dev/null || true)
fi

log "Done. PR: $PR_URL"

# Output JSON for n8n
echo "{\"repo_url\": \"https://github.com/$OWNER/$APP_NAME\", \"winner_branch\": \"$WINNER\", \"pr_url\": \"$PR_URL\", \"status\": \"success\"}" > "$RUN_DIR/result.json"
