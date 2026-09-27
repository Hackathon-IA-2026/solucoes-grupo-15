---
question: Como backend, `ai` e a borda (CloudFront/ALB) registram logs e eventos na AWS — grupos do CloudWatch, retenção, correlação por `request_id` — o suficiente para depurar a demo e sustentar a avaliação do M4, dentro da postura de economia?
status: resolved
resolved_at: 2026-09-27
blocked_by: []
claimed_by: s-2026-09-27-issues-99-100
concerns:
  - i6-telemetry
  - i11-cost
created_at: 2026-09-26
---

Issue: https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/99 (sub-issue de #89)

## Notes

Saiu do Fog "Observabilidade na AWS" (I6) em 2026-09-26, a pedido de Eduardo ao fechar o topic-cognito-auth. A I6 ficou `partial`: o `user_id` dos eventos vem do token, mas `carolina`/`equipe` usam uma senha de demo compartilhada, então um evento não identifica um avaliador específico.

Evidência levantada (s-2026-09-27-issues-99-100): o backend e o `ai` não configuram `logging` e só escrevem o access log do uvicorn no stdout. O `request_id` existe só como id da busca (`routes/search.py:221`, uuid4) e fica gravado em `SearchExecution` no Postgres com o resultado bruto e as versões (`models.py:282`). `POST /v1/search/{request_id}/replay` e `python -m app.replay <request_id>` reexecutam a busca sem rede nem IA. A sondagem de 2026-09-26 confirmou que o participante cria recursos de CloudWatch Logs. O ALB acrescenta `X-Amzn-Trace-Id` a toda requisição que chega ao backend.

Decisão (Eduardo, 2026-09-27, por delegação: "resolva as issues #99 e #100 com as recomendações indicadas pelo agente"): recomendação do agente aceita sem alteração.

## Synthesis

Resolvido em 2026-09-27.

- **Grupos e retenção.** Driver `awslogs` nas duas task definitions, com um grupo por serviço (`/capiwatt/backend` e `/capiwatt/ai`) criado pelo CDK. Retenção de 3 dias (a conta dura 72 h) e `RemovalPolicy.DESTROY`.
- **Borda.** Sem access logs do ALB nem logs padrão do CloudFront: os dois exigem bucket S3 e política própria. Para a borda bastam as métricas gratuitas do CloudWatch (5xx, latência e contagem de requisições). Também ficam de fora Container Insights, X-Ray, alarmes e dashboards.
- **Correlação.** O backend ganha um middleware que escreve uma linha JSON no stdout por requisição, com `ts`, `method`, `path`, `status`, `duration_ms`, `user_id` (do token, `-` no modo `none`), `trace_id` e `search_request_id`.
  - `trace_id` vem do header `X-Amzn-Trace-Id` posto pelo ALB (`-` no Compose local).
  - `search_request_id` só aparece em `/v1/search`.
  - A linha não leva corpo, texto da consulta, token nem senha. O texto e o resultado da consulta já ficam em `SearchExecution`, acessíveis pelo `request_id`.
  - O mesmo formato vale no Compose, sem diferença entre ambientes.
- **Serviço `ai`.** O código do `ai` não muda (preferência de Eduardo, topic-vector-index-hosting); o access log do uvicorn no grupo `/capiwatt/ai` basta. Numa demo com pouco tráfego, a correlação backend→`ai` é pelo horário.
- **Depuração.** Depurar uma busca: achar o `search_request_id` no Logs Insights, depois rodar o replay ou `python -m app.replay` via ECS Exec. Essas duas consultas do Logs Insights ficam no README de `hackathon/infra/`.
- **Avaliação do M4.** A evidência do M4 é o artefato da comparação (topic-tb1-aws-vs-local) mais a linha `SearchExecution` da AWS. Os logs só dão a trilha e não guardam resultado.
- **Atribuição.** O limite de atribuição de `carolina`/`equipe` fica aceito, sem contas por avaliador. Quem precisar de atribuição individual usa as contas opcionais de `COGNITO_USERS`.
- **Custo.** A ingestão de logs da demo fica abaixo de 0,1 GB (< US$ 0,05). Com isso a estimativa total de custo do M4 fecha em [I11](../concerns/i11-cost.md).

Concerns: [I6](../concerns/i6-telemetry.md) `resolved`, [I11](../concerns/i11-cost.md) `resolved`. Contratos de fronteira inalterados: não há header nem campo novo, e `trace_id` é só lido.
