---
question: Onde o frontend estático é hospedado (S3 website só HTTP, ou outra opção com HTTPS) e como ele chega ao backend (CORS vs. proxy /v1)?
status: resolved
blocked_by:
  - topic-backend-entry
claimed_by: s-2026-09-26-aws-arch
concerns:
  - i9-integration
  - u6-acceptance
created_at: 2026-09-26
resolved_at: 2026-09-26
---

## Notes

Resolução (Eduardo, 2026-09-26, "aceito as sugestões"): bucket S3 privado + OAC atrás do CloudFront único; `cdk deploy` roda `npm run build` e publica `dist/` via `BucketDeployment` (com invalidação); CloudFront Function no comportamento padrão reescreve caminhos sem extensão para `/index.html` (sem error responses globais, preservando 403/404 da API); `config.json` em runtime gerado pelo CDK com `{region, userPoolId, userPoolClientId}`; sem Cognito no `config.json` → modo demo sem login (local); `index.html`/`config.json` no-cache, assets com hash com cache longo.
