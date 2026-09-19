---
name: sonarqube-runner
description: Runs SonarQube or SonarCloud static analysis scans and queries unresolved code quality or security issues via REST API or Docker, outputting sonar-report.json for the AI Gatekeeper.
---

# SonarQube Runner Skill

This skill teaches the agent how to run static analysis with SonarQube / SonarCloud, or query unresolved issues directly via REST API, outputting a standard `sonar-report.json` for consumption by the AI Quality Gatekeeper.

---

## Capabilities & Integration Modes

The runner supports two primary workflows depending on your environment:

### Mode 1: Direct API Query (Recommended for Personal Projects & Cloud CI)
For personal and open source projects, consuming SonarCloud via REST API is lightweight and requires no local scanner installation:
- SonarCloud provides free analysis for public GitHub repositories.
- When configured with `SONAR_HOST_URL`, `SONAR_TOKEN`, and `SONAR_PROJECT_KEY`, the agent fetches unresolved code smells and vulnerabilities directly.
- The results are parsed and formatted into `sonar-report.json` in the target repository.

### Mode 2: Docker Scanner Execution (Zero Host Installation)
If a local code scan is required before committing (or on private corporate repositories without public cloud integration), the runner uses the official `sonarsource/sonar-scanner-cli` Docker image.

---

## Environment Configuration

Configure the following variables in `.env` or CI/CD environment secrets:

```bash
# Personal / Small Projects (SonarCloud)
SONAR_HOST_URL=https://sonarcloud.io
SONAR_TOKEN=your_sonarcloud_token
SONAR_PROJECT_KEY=your_project_key
PR_NUMBER= # Optional: filter by pull request number

# Corporate Projects (Internal On-Premise SonarQube)
SONAR_HOST_URL=http://sonar.internal.company.com:9000
SONAR_TOKEN=sqp_your_corporate_token
SONAR_PROJECT_KEY=internal_project_key
```

---

## Agent Procedures

### Procedure 1: Fetch Issues via REST API

Run the helper script to query the active issues from SonarQube/SonarCloud:

```bash
bash .agents/skills/sonarqube-runner/scripts/run_sonar.sh --target . --api
```

This queries `${SONAR_HOST_URL}/api/issues/search`, extracts unresolved blocker, critical, and major issues, and writes `sonar-report.json` to the target directory.

### Procedure 2: Run Full Local Scan via Docker

When local static analysis execution is desired before pushing:

```bash
bash .agents/skills/sonarqube-runner/scripts/run_sonar.sh --target . --scan
```

This mounts the target repository into `sonarsource/sonar-scanner-cli`, connects to your configured Sonar server, and exports the report.

### Procedure 3: Offline / Dry-Run Verification

If no live Sonar server is configured, the skill verifies that the workspace can proceed cleanly without Sonar blocking:
- If `sonar-report.json` does not exist and no API credentials are provided, `sonar_adapter.py` returns `[PASSED] No SonarQube issues detected.`
- This guarantees zero disruption for offline or local development.
