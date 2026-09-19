---
name: context-harness
description: Scans the repository documentation (guidelines, RFCs, ADRs), updates project rules, and generates a local JSON embedding index (context_harness.json) for semantic retrieval.
---

# Context Harness Builder Skill

This skill teaches the agent how to scan the repository, extract architectural norms and guidelines, and generate a local vector embedding index (`context_harness.json`) for the AI Quality Gatekeeper.

## Workflow

1. **Discover Documentation**:
   - Inspect `docs/guidelines.md` and any other architectural markdown files under `docs/`, `rfc/`, or `adr/`.
   - Ensure the guidelines reflect the latest architectural decisions and compliance standards.

2. **Index Generation**:
   - Run the indexing script:
     ```bash
     python build_harness.py --docs docs README.md --output context_harness.json
     ```
   - If running inside Docker:
     ```bash
     docker compose run --rm -e GOOGLE_API_KEY=$GOOGLE_API_KEY gatekeeper python build_harness.py
     ```

3. **Verify Retrieval**:
   - Confirm that `context_harness.json` has been created with chunk metadata and vector embeddings.
   - When reviewing PRs, `gatekeeper.py` will automatically load this index to semantically match diffs against relevant guidelines.
