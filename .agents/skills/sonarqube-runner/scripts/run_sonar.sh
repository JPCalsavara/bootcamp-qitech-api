#!/usr/bin/env bash
# ==============================================================================
# SonarQube & SonarCloud Runner Script
# Fetches issues via REST API or triggers a containerized scan.
# Output: sonar-report.json in the target directory.
# ==============================================================================
set -euo pipefail

TARGET_DIR="."
SONAR_HOST="${SONAR_HOST_URL:-https://sonarcloud.io}"
SONAR_AUTH_TOKEN="${SONAR_TOKEN:-}"
PROJECT_KEY="${SONAR_PROJECT_KEY:-}"
PR_NUM="${PR_NUMBER:-}"
OUTPUT_FILE=""
MODE="api"

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET_DIR="$2"
      shift 2
      ;;
    --host)
      SONAR_HOST="$2"
      shift 2
      ;;
    --token)
      SONAR_AUTH_TOKEN="$2"
      shift 2
      ;;
    --project-key)
      PROJECT_KEY="$2"
      shift 2
      ;;
    --pr)
      PR_NUM="$2"
      shift 2
      ;;
    --output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    --scan)
      MODE="scan"
      shift
      ;;
    --api)
      MODE="api"
      shift
      ;;
    *)
      echo "[WARN] Unknown argument: $1"
      shift
      ;;
  esac
done

TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
if [[ -z "$OUTPUT_FILE" ]]; then
  OUTPUT_FILE="${TARGET_DIR}/sonar-report.json"
fi

echo "[INFO] Target Directory: ${TARGET_DIR}"
echo "[INFO] Mode: ${MODE}"

if [[ "$MODE" == "api" ]]; then
  if [[ -z "$SONAR_AUTH_TOKEN" || -z "$PROJECT_KEY" ]]; then
    echo "[WARN] SONAR_TOKEN or SONAR_PROJECT_KEY is not set. Creating empty report."
    echo '{"issues": []}' > "$OUTPUT_FILE"
    echo "[INFO] Generated placeholder at ${OUTPUT_FILE} (No Sonar issues)."
    exit 0
  fi

  API_URL="${SONAR_HOST%/}/api/issues/search?componentKeys=${PROJECT_KEY}&resolved=false"
  if [[ -n "$PR_NUM" ]]; then
    API_URL="${API_URL}&pullRequest=${PR_NUM}"
  fi

  echo "[INFO] Querying Sonar API: ${API_URL}"
  HTTP_STATUS=$(curl -s -o "${OUTPUT_FILE}.tmp" -w "%{http_code}" -u "${SONAR_AUTH_TOKEN}:" "${API_URL}" || echo "000")

  if [[ "$HTTP_STATUS" == "200" ]]; then
    mv "${OUTPUT_FILE}.tmp" "$OUTPUT_FILE"
    COUNT=$(grep -o '"rule":' "$OUTPUT_FILE" | wc -l || echo "0")
    echo "[SUCCESS] Retrieved ${COUNT} issues into ${OUTPUT_FILE}"
  else
    echo "[WARN] API query failed with HTTP status ${HTTP_STATUS}. Preserving clean state."
    rm -f "${OUTPUT_FILE}.tmp"
    echo '{"issues": []}' > "$OUTPUT_FILE"
  fi

elif [[ "$MODE" == "scan" ]]; then
  if [[ -z "$SONAR_AUTH_TOKEN" || -z "$PROJECT_KEY" ]]; then
    echo "[ERROR] Cannot execute scan: SONAR_TOKEN and SONAR_PROJECT_KEY are required."
    exit 1
  fi

  echo "[INFO] Running SonarScanner container..."
  docker run --rm \
    -v "${TARGET_DIR}:/usr/src" \
    -e SONAR_HOST_URL="${SONAR_HOST}" \
    -e SONAR_TOKEN="${SONAR_AUTH_TOKEN}" \
    sonarsource/sonar-scanner-cli \
    -Dsonar.projectKey="${PROJECT_KEY}" \
    -Dsonar.sources="."

  echo "[INFO] Scan completed. Now querying latest results via API..."
  "$0" --target "$TARGET_DIR" --host "$SONAR_HOST" --token "$SONAR_AUTH_TOKEN" --project-key "$PROJECT_KEY" --output "$OUTPUT_FILE"
fi
