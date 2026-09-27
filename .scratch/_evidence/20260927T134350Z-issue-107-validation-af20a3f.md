# Evidence Pack

- **Pack ID:** EVP-107-af20a3f
- **Template version:** 1.0
- **Generated at (UTC):** 2026-09-27T13:43:50Z
- **Overall status:** PARTIAL (the six acceptance criteria PASS; destroy and cleanup proof remain pending)
- **Task mode:** github (local recovery copy; publication awaits the owner's specific approval)
- **Task reference:** Hackathon-IA-2026/solucoes-grupo-15#107
- **Repository:** Hackathon-IA-2026/solucoes-grupo-15
- **Branch:** docs/perspec-me-issues-99-100
- **Base revision:** bd919ed
- **Current revision:** af20a3f (infrastructure commit 60c36f0 plus frontend contract fix)
- **Working-tree state:** dirty from pre-existing perspec-me edits and untracked .scratch; hackathon code is clean
- **Producer:** Codex, continuation of the #107 session

## 1. Executive result

The three deployed stacks remain complete. The CloudFront distribution serves the S3 frontend with SPA fallback, runtime config, the expected cache policies and JSON API errors. The frontend contract fix in af20a3f was deployed by updating only CapiwattCompute. Live browser verification now renders search results and submits feedback successfully. All six acceptance criteria pass. Destruction and the proof of no remaining resources await the owner's approval; no push or issue comment was made.

This pack supersedes the PARTIAL result for search and feedback in the earlier local pack, .scratch/_evidence/20260927T131252Z-issue-107-frontend-s3-cloudfront.md (SHA-256 b75bf93f772b35db86d7a328f8393159448e8cd5c7323b7ac00fcb33ce6457f1). It reuses that pack's unchanged OAC and first deployment evidence.

## 2. Scope-to-proof map

| Claim ID | Requirement or property | Source | Verification | Evidence IDs | Status |
| -------- | ------------------------ | ------ | ------------ | ------------ | ------ |
| CLM-001 | CloudFront opens the demo app | AC 1 | Earlier browser session plus current / and config checks | EVD-001, EVD-005 | PASS |
| CLM-002 | API calls use the same origin | AC 1 | Earlier 48-call browser trace; current search and feedback URLs checked against CloudFront host | EVD-001, EVD-004 | PASS |
| CLM-003 | Document view works | AC 1 | Earlier live document screen and 200 API response | EVD-001 | PASS |
| CLM-004 | Graph view works | AC 1 | Earlier live graph panel and 200 API response | EVD-001 | PASS |
| CLM-005 | Notifications work | AC 1 | Earlier live notification UI and 200 API responses | EVD-001 | PASS |
| CLM-006 | Search renders results | AC 1 | Current browser: 200, 10 chunks, 10 visible cards, no page error | EVD-002, EVD-004 | PASS |
| CLM-007 | Feedback submits successfully | AC 1 | Current browser click: 200, chunk identity in request, success message | EVD-002, EVD-004 | PASS |
| CLM-008 | Deep links load the SPA | AC 2 | Current /explorar and dotted encoded process path return HTML 200; earlier browser rendered both pages | EVD-001, EVD-005 | PASS |
| CLM-009 | Unknown API document returns JSON 404 | AC 3 | Current HTTP response: 404 application/json | EVD-005 | PASS |
| CLM-010 | Shell and config no-cache; hashed assets long-cache | AC 4 | Current HTTP headers and new JS asset | EVD-005 | PASS |
| CLM-011 | Synth tests cover OAC, Function association and no global error fallback | AC 5 | Earlier 22-test infra suite and mutation check, code unchanged | EVD-001 | PASS |
| CLM-012 | Frontend change appears after deploy | AC 6 | Earlier explicit invalidation probe; current changed JS asset visible after Compute update | EVD-001, EVD-003, EVD-005 | PASS |
| CLM-013 | S3 bucket is private and read through OAC | Issue scope | Earlier S3 block/policy/direct-403 checks; no bucket/policy update in this deployment | EVD-001, EVD-003 | PASS |
| CLM-014 | Function keeps static files and dotted IDs correct | Issue scope | Earlier Function tests; current HTML deep link and JS 200 | EVD-001, EVD-005 | PASS |
| CLM-015 | Destroy leaves no frontend bucket or Lambda logs | Cleanup rule | Construct tests and current log-group checks in earlier pack; actual destroy has not run | EVD-001 | PARTIAL |

## 3. Change inventory

- **Added:** S3/OAC frontend construct and SPA CloudFront Function in 60c36f0.
- **Modified:** Compute default behavior and synth tests in 60c36f0. Frontend search/feedback adapters, their UI callers and tests, and requirements/contracts/frontend-backend.md in af20a3f.
- **Deleted:** none.
- **Config/schema changes:** generated /config.json remains {"region":"us-west-2"} with no Cognito fields.
- **Externally visible behaviour changes:** search cards display flat chunk results; feedback sends document_version and chunk_index. Static frontend JS changed to assets/index-Blm2ZB54.js.
- **Intentionally untouched:** backend application code, Cognito #108, #109, the user's uncommitted perspec-me work and main branch.

## 4. Verification bundle

- **Tests run:** earlier 22 infra tests; subagent reported 64/64 frontend tests, build and lint on af20a3f. The subagent's raw test log was not retained in this pack.
- **Newly added tests:** frontend search and feedback regression assertions in af20a3f; infra OAC, Function and deployment tests in 60c36f0.
- **Edge/failure cases covered:** dotted process IDs, JSON 404 for API, no-cache shell, immutable hashed asset, formerly failing flat search response and required feedback fields.
- **Integration/e2e checks:** CloudFront HTTP checks and Playwright search/feedback on the live stack, after the targeted Compute deploy.
- **Skipped or unavailable checks:** destroy and orphan-resource scan pending explicit approval; frontend Docker bundling fallback not exercised.

| Command | Exit code | Result | Evidence ID |
| ------- | --------- | ------ | ----------- |
| aws cloudformation describe-stacks for Network, Data and Compute (13:33Z) | 0 | CREATE_COMPLETE, CREATE_COMPLETE, UPDATE_COMPLETE before fix | EVD-006 |
| npx -y aws-cdk@2.1143.0 deploy CapiwattCompute --exclusively --require-approval never -c opensearch_service_linked_role=existing (with .env and prior venv) | 0 | Compute UPDATE_COMPLETE; new frontend asset deployed; only Compute stack selected | EVD-003 |
| node scratchpad/pw/e2e-fixed.mjs [CloudFront URL] | 0 | Search 200 with 10 rendered cards; feedback 200 with chunk identity; no page errors | EVD-004 |
| curl CloudFront shell, config, JS and deep links | 0 | 200; expected cache/content-type; new JS hash; API unknown document 404 JSON | EVD-005 |
| git show --check af20a3f | 0 | no whitespace errors | EVD-002 |

## 5. Engineering hygiene

| Category | Status | Evidence ID |
| -------- | ------ | ----------- |
| Linting | PASS (subagent reported npm run lint; earlier infra ruff PASS) | EVD-002, EVD-001 |
| Formatting | PASS (earlier infra ruff format check; git show --check on af20a3f) | EVD-001, EVD-002 |
| Static analysis | NOT_RUN (cfn-lint) | — |
| Type checking | PASS (subagent reported npm run build, which runs tsc -b; current CDK build also ran it) | EVD-002, EVD-003 |
| Build | PASS (current CDK Vite build and deploy) | EVD-003 |
| Repo-specific architectural rules / coding standards | PASS (frontend calls backend only through /v1; ADR-0002 deployment path; contract snapshot updated) | EVD-002, EVD-003 |

## 6. Plan ledger and deviations

- **Conceptual plan:** validate the already deployed #107 stack; fix any failed acceptance behavior; commit and redeploy only what is needed; record evidence; stop before destroy, push and issue comment.
- **Executed approach:** reused the existing deployment and pack, confirmed stack/HTTP state, fixed the two pre-existing frontend contract mismatches, committed af20a3f, deployed CapiwattCompute exclusively, ran live browser and HTTP checks.
- **Deviations:** first local CDK invocation failed before AWS interaction because aws_cdk was absent from the default Python environment. Repeated it with the prior venv. CloudFormation also updated the backend task definition/service inside Compute; backend application code was not changed, and live API requests succeeded. No Network/Data redeploy occurred.

## 7. Rationale and trade-offs

- **Approach taken:** adapt frontend consumers to the existing flat chunk contract, preserving backend API and search ranking. Update the boundary snapshot to reflect the API already deployed.
- **Alternatives considered:** changing backend responses back to grouped results; excluded because #78 and #82 already established chunk search and feedback identity.
- **Why rejected:** would reverse existing backend contracts and widen the deployment.
- **Known trade-offs:** the Explore page now shows one card per chunk, so a family can appear more than once.

## 8. Exploration archive

- Earlier pack records the original interrupted deploy, OAC checks, full UI walk-through and explicit cache invalidation probe. The first current CDK invocation failed locally with ModuleNotFoundError: No module named aws_cdk, exit 1; it did not create a CloudFormation change set.

## 9. Risks, rollback, and limitations

- **Residual risk / blast radius:** the public demo stack remains online with AUTH_MODE=none. Compute's backend task/service updated during the frontend redeploy, though API smoke and live search/feedback passed.
- **Rollback approach:** revert af20a3f for the frontend contract change or 60c36f0 for hosting, then deploy Compute; destroy requires owner approval.
- **Incomplete work:** actual destroy, orphan-resource scan and evidence publication.
- **Assumptions:** the earlier pack accurately records its timestamped tests and S3 policy checks; unchanged constructs and stack events support reuse.
- **Environment limitations:** the participant role cannot read CloudFront configuration directly; HTTP behavior and S3 policy were used.
- **Missing evidence:** raw subagent test output and post-destroy scan.
- **Follow-up work:** obtain separate approval before destroy, push or commenting on #107. After that, proceed directly to #110 and skip #108/#109 as directed.

## 10. Chain of custody

| ID | Producer / generated UTC | Command/tool and revision | Pointer | SHA-256 |
| -- | ------------------------ | ------------------------- | ------- | ------- |
| EVD-001 | Claude Code / 13:13Z | earlier #107 verification, 60c36f0 | .scratch/_evidence/20260927T131252Z-issue-107-frontend-s3-cloudfront.md | b75bf93f772b35db86d7a328f8393159448e8cd5c7323b7ac00fcb33ce6457f1 |
| EVD-002 | subagent / 13:37Z | git show --check and reported frontend test/build/lint, af20a3f | commit af20a3f; agent completion message (no raw test log) | — |
| EVD-003 | Codex / 13:42:08Z | CDK 2.1143.0 targeted deploy, af20a3f | .scratch/_evidence/artifacts-107/compute-frontend-fix-deploy.log | 797d922692ca37d9889b66b239d51a3cacfe357af70ad40b064711389df47d28 |
| EVD-004 | Codex / 13:42:33Z | Playwright via e2e-fixed.mjs, af20a3f | .scratch/_evidence/artifacts-107/e2e-fixed.log | 1f82da5d619d058e0eb8e956aadb128b90a6cac5746d7d670cb8e77f9465ad0d |
| EVD-005 | Codex / 13:42:58Z | curl live CloudFront, af20a3f | .scratch/_evidence/artifacts-107/cache-after-fix.log; config-after-fix.log; http-after-fix.log; js-asset-after-fix.log | 256feae68def540df51ea5f9ef07f9f6ce0adae1235b6bc0e7dffe1c45982dde (cache log) |
| EVD-006 | Codex / 13:33:34Z | AWS CLI describe-stacks, 60c36f0 | .scratch/_evidence/artifacts-107/stacks-before-fix.log | 75449a56ec5dcca0d8e3fe9f584b1d720b93dc49d6a1540c4761f6dc9f097c74 |

## 11. Machine-readable manifest

<!-- evidence-manifest:start -->

```yaml
manifest_version: "1.0"
pack_id: "EVP-107-af20a3f"
task:
  mode: "github"
  reference: "Hackathon-IA-2026/solucoes-grupo-15#107"
repository:
  branch: "docs/perspec-me-issues-99-100"
  base_revision: "bd919ed"
  current_revision: "af20a3f"
generated:
  at_utc: "2026-09-27T13:43:50Z"
  producer: "Codex"
claims:
  - {id: "CLM-001", status: "PASS", evidence_ids: ["EVD-001", "EVD-005"]}
  - {id: "CLM-002", status: "PASS", evidence_ids: ["EVD-001", "EVD-004"]}
  - {id: "CLM-003", status: "PASS", evidence_ids: ["EVD-001"]}
  - {id: "CLM-004", status: "PASS", evidence_ids: ["EVD-001"]}
  - {id: "CLM-005", status: "PASS", evidence_ids: ["EVD-001"]}
  - {id: "CLM-006", status: "PASS", evidence_ids: ["EVD-002", "EVD-004"]}
  - {id: "CLM-007", status: "PASS", evidence_ids: ["EVD-002", "EVD-004"]}
  - {id: "CLM-008", status: "PASS", evidence_ids: ["EVD-001", "EVD-005"]}
  - {id: "CLM-009", status: "PASS", evidence_ids: ["EVD-005"]}
  - {id: "CLM-010", status: "PASS", evidence_ids: ["EVD-005"]}
  - {id: "CLM-011", status: "PASS", evidence_ids: ["EVD-001"]}
  - {id: "CLM-012", status: "PASS", evidence_ids: ["EVD-001", "EVD-003", "EVD-005"]}
  - {id: "CLM-013", status: "PASS", evidence_ids: ["EVD-001", "EVD-003"]}
  - {id: "CLM-014", status: "PASS", evidence_ids: ["EVD-001", "EVD-005"]}
  - {id: "CLM-015", status: "PARTIAL", evidence_ids: ["EVD-001"]}
artifacts:
  - {id: "EVD-001", category: "log", status: "PASS", claim_ids: ["CLM-001", "CLM-002", "CLM-003", "CLM-004", "CLM-005", "CLM-008", "CLM-011", "CLM-012", "CLM-013", "CLM-014", "CLM-015"], command: "see prior pack", working_directory: "repository root", exit_code: 0, pointer: ".scratch/_evidence/20260927T131252Z-issue-107-frontend-s3-cloudfront.md", sha256: "b75bf93f772b35db86d7a328f8393159448e8cd5c7323b7ac00fcb33ce6457f1", generated_at_utc: "2026-09-27T13:13Z", producer: "Claude Code", tool: "multiple", tool_version: ""}
  - {id: "EVD-002", category: "diff", status: "PASS", claim_ids: ["CLM-006", "CLM-007"], command: "git show --check af20a3f; git show af20a3f", working_directory: "repository root", exit_code: 0, pointer: "commit af20a3f and subagent completion message", sha256: "", generated_at_utc: "2026-09-27T13:37Z", producer: "Codex and subagent", tool: "git", tool_version: ""}
  - {id: "EVD-003", category: "build", status: "PASS", claim_ids: ["CLM-012", "CLM-013"], command: "npx -y aws-cdk@2.1143.0 deploy CapiwattCompute --exclusively --require-approval never -c opensearch_service_linked_role=existing", working_directory: "hackathon/infra", exit_code: 0, pointer: ".scratch/_evidence/artifacts-107/compute-frontend-fix-deploy.log", sha256: "797d922692ca37d9889b66b239d51a3cacfe357af70ad40b064711389df47d28", generated_at_utc: "2026-09-27T13:42:08Z", producer: "Codex", tool: "CDK CLI", tool_version: "2.1143.0"}
  - {id: "EVD-004", category: "test", status: "PASS", claim_ids: ["CLM-002", "CLM-006", "CLM-007"], command: "node scratchpad/pw/e2e-fixed.mjs [CloudFront URL]", working_directory: "repository root", exit_code: 0, pointer: ".scratch/_evidence/artifacts-107/e2e-fixed.log", sha256: "1f82da5d619d058e0eb8e956aadb128b90a6cac5746d7d670cb8e77f9465ad0d", generated_at_utc: "2026-09-27T13:42:33Z", producer: "Codex", tool: "Playwright", tool_version: "1.61.1"}
  - {id: "EVD-005", category: "test", status: "PASS", claim_ids: ["CLM-001", "CLM-008", "CLM-009", "CLM-010", "CLM-012", "CLM-014"], command: "curl live CloudFront paths and headers", working_directory: "repository root", exit_code: 0, pointer: ".scratch/_evidence/artifacts-107/cache-after-fix.log", sha256: "256feae68def540df51ea5f9ef07f9f6ce0adae1235b6bc0e7dffe1c45982dde", generated_at_utc: "2026-09-27T13:42:58Z", producer: "Codex", tool: "curl", tool_version: ""}
  - {id: "EVD-006", category: "other", status: "PASS", claim_ids: ["CLM-001"], command: "aws cloudformation describe-stacks for CapiwattNetwork CapiwattData CapiwattCompute", working_directory: "repository root", exit_code: 0, pointer: ".scratch/_evidence/artifacts-107/stacks-before-fix.log", sha256: "75449a56ec5dcca0d8e3fe9f584b1d720b93dc49d6a1540c4761f6dc9f097c74", generated_at_utc: "2026-09-27T13:33:34Z", producer: "Codex", tool: "AWS CLI", tool_version: ""}
```

<!-- evidence-manifest:end -->

<!-- evidence-pack:#107:af20a3f -->
