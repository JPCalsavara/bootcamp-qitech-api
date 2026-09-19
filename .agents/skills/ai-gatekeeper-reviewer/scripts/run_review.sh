#!/usr/bin/env bash
# ==============================================================================
# Universal AI Gatekeeper Reviewer Orchestrator
# Runs test suite, SonarQube issue sync, diff extraction, and LangGraph Gatekeeper.
# Compatible with Copilot, AGY, Claude Code, and GPT / Cursor.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATEKEEPER_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

TARGET_DIR="."
BASE_BRANCH="main"
SKIP_TESTS=false
SKIP_SONAR=false
SKIP_HARNESS=false
APPLY_PATCH=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET_DIR="$2"
      shift 2
      ;;
    --base)
      BASE_BRANCH="$2"
      shift 2
      ;;
    --skip-tests)
      SKIP_TESTS=true
      shift
      ;;
    --skip-sonar)
      SKIP_SONAR=true
      shift
      ;;
    --skip-harness)
      SKIP_HARNESS=true
      shift
      ;;
    --apply-patch)
      APPLY_PATCH=true
      shift
      ;;
    *)
      echo "[WARN] Unknown option: $1"
      shift
      ;;
  esac
done

TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
echo "=== AI Quality Gatekeeper Review Orchestrator ==="
echo "[INFO] Target Project: ${TARGET_DIR}"
echo "[INFO] Gatekeeper System: ${GATEKEEPER_ROOT}"

# 1. Run Tests (if not skipped)
if [[ "$SKIP_TESTS" == false ]]; then
  echo "[STEP 1/5] Running project test suite..."
  if [[ -f "${TARGET_DIR}/package.json" ]]; then
    echo "[INFO] Detected Node.js / TypeScript project."
    npm --prefix "$TARGET_DIR" test > "${TARGET_DIR}/tests.log" 2>&1 || true
  elif [[ -f "${TARGET_DIR}/pytest.ini" || -d "${TARGET_DIR}/tests" ]]; then
    echo "[INFO] Detected Python project."
    pytest "$TARGET_DIR" > "${TARGET_DIR}/tests.log" 2>&1 || true
  elif [[ -f "${TARGET_DIR}/go.mod" ]]; then
    echo "[INFO] Detected Go project."
    (cd "$TARGET_DIR" && go test ./... > "tests.log" 2>&1 || true)
  elif [[ -f "${TARGET_DIR}/Cargo.toml" ]]; then
    echo "[INFO] Detected Rust project."
    (cd "$TARGET_DIR" && cargo test > "tests.log" 2>&1 || true)
  else
    echo "[INFO] No recognized test runner found. Recording empty test logs."
    touch "${TARGET_DIR}/tests.log"
  fi
else
  echo "[STEP 1/5] Skipping test execution (--skip-tests)."
fi

# 2. Extract Git Diff
echo "[STEP 2/5] Extracting Git diff..."
DIFF_FILE="${TARGET_DIR}/diff.txt"

# Auto-heal shallow repositories (common in CI/CD environments like GitHub Actions)
if [[ "$(git -C "$TARGET_DIR" rev-parse --is-shallow-repository 2>/dev/null || echo "false")" == "true" ]]; then
  echo "[INFO] Shallow Git clone detected. Fetching historical commits for base branch..."
  git -C "$TARGET_DIR" fetch --depth=50 origin "$BASE_BRANCH" 2>/dev/null || true
fi

# First check if there is an unstaged or staged working tree diff
git -C "$TARGET_DIR" diff > "$DIFF_FILE" || true
if [[ ! -s "$DIFF_FILE" ]]; then
  # Fallback to diff against base branch or HEAD~1
  if git -C "$TARGET_DIR" rev-parse --verify "$BASE_BRANCH" >/dev/null 2>&1; then
    echo "[INFO] Diffing against branch ${BASE_BRANCH}..."
    git -C "$TARGET_DIR" diff "$BASE_BRANCH"...HEAD > "$DIFF_FILE" || true
  elif git -C "$TARGET_DIR" rev-parse --verify HEAD~1 >/dev/null 2>&1; then
    echo "[INFO] Diffing against HEAD~1..."
    git -C "$TARGET_DIR" diff HEAD~1 > "$DIFF_FILE" || true
  fi
fi

if [[ ! -s "$DIFF_FILE" ]]; then
  echo "[WARN] Diff is empty in ${TARGET_DIR}. Nothing to review."
  exit 0
fi
echo "[INFO] Diff extracted ($(wc -l < "$DIFF_FILE") lines)."

# 3. SonarQube Issue Retrieval
if [[ "$SKIP_SONAR" == false ]]; then
  echo "[STEP 3/5] Checking SonarQube issues..."
  SONAR_RUNNER="${GATEKEEPER_ROOT}/.agents/skills/sonarqube-runner/scripts/run_sonar.sh"
  if [[ -f "$SONAR_RUNNER" ]]; then
    bash "$SONAR_RUNNER" --target "$TARGET_DIR" --api
  fi
else
  echo "[STEP 3/5] Skipping SonarQube retrieval (--skip-sonar)."
fi

# 4. Context Harness Indexing
if [[ "$SKIP_HARNESS" == false ]]; then
  echo "[STEP 4/5] Checking Context Harness index..."
  HARNESS_FILE="${TARGET_DIR}/context_harness.json"
  if [[ ! -f "$HARNESS_FILE" ]]; then
    echo "[INFO] Building Context Harness vector index..."
    DOCS_ARGS=()
    [[ -d "${TARGET_DIR}/docs" ]] && DOCS_ARGS+=("${TARGET_DIR}/docs")
    [[ -f "${TARGET_DIR}/README.md" ]] && DOCS_ARGS+=("${TARGET_DIR}/README.md")
    for spec in "${TARGET_DIR}"/SPEC-*.md; do
      [[ -f "$spec" ]] && DOCS_ARGS+=("$spec")
    done

    if [[ ${#DOCS_ARGS[@]} -gt 0 ]]; then
      python3 "${GATEKEEPER_ROOT}/build_harness.py" --docs "${DOCS_ARGS[@]}" --output "$HARNESS_FILE" || true
    fi
  else
    echo "[INFO] Existing harness index found at ${HARNESS_FILE}."
  fi
fi

# 5. Execute LangGraph Gatekeeper
echo "[STEP 5/5] Executing AI Quality Gatekeeper..."
EXIT_CODE=0
GATEKEEPER_ARGS=(--target /target)
[[ "$APPLY_PATCH" == true ]] && GATEKEEPER_ARGS+=(--apply-patch)

LOCAL_GATEKEEPER_ARGS=(--target "$TARGET_DIR")
[[ "$APPLY_PATCH" == true ]] && LOCAL_GATEKEEPER_ARGS+=(--apply-patch)

if command -v docker &>/dev/null && [[ -f "${GATEKEEPER_ROOT}/docker-compose.yml" ]]; then
  docker compose -f "${GATEKEEPER_ROOT}/docker-compose.yml" run --rm \
    -v "${TARGET_DIR}:/target" \
    test python3 -u gatekeeper.py "${GATEKEEPER_ARGS[@]}" || EXIT_CODE=$?
else
  python3 "${GATEKEEPER_ROOT}/gatekeeper.py" "${LOCAL_GATEKEEPER_ARGS[@]}" || EXIT_CODE=$?
fi

echo "=== Review Completed ==="
if [[ -f "${TARGET_DIR}/report.md" ]]; then
  echo "[INFO] Report generated at: ${TARGET_DIR}/report.md"
fi

exit "$EXIT_CODE"
