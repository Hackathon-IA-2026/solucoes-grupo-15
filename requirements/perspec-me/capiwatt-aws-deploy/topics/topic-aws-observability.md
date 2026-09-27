---
question: Como backend, `ai` e a borda (CloudFront/ALB) registram logs e eventos na AWS — grupos do CloudWatch, retenção, correlação por `request_id` — o suficiente para depurar a demo e sustentar a avaliação do M4, dentro da postura de economia?
status: open
blocked_by: []
claimed_by:
concerns:
  - i6-telemetry
  - i11-cost
created_at: 2026-09-26
---

Issue: https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/99 (sub-issue de #89)

## Notes

Saiu do Fog "Observabilidade na AWS" (I6) em 2026-09-26, a pedido de Eduardo ao fechar o topic-cognito-auth. A I6 ficou `partial`: o `user_id` dos eventos vem do token, mas `carolina`/`equipe` usam uma senha de demo compartilhada, então um evento não identifica um avaliador específico.
