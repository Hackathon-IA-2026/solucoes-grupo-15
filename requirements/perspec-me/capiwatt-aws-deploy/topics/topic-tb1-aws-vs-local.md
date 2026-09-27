---
question: A comparação do TB1 repetido na AWS com a avaliação local (critério de saída do M4) entra na Destination deste Map — e, se entrar, quais métricas, qual corpus e qual critério de equivalência são comparados?
status: open
blocked_by: []
claimed_by:
concerns:
  - m5-performance-metrics
  - i7-reproducibility
created_at: 2026-09-26
---

Issue: https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/100 (sub-issue de #89)

## Notes

Saiu do Fog "Comparação TB1 AWS × local" (O/M) em 2026-09-26, a pedido de Eduardo. O plano de execução (`hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md:252`) define o critério de saída do M4 como "TB1 repetido na AWS e resultados comparados à avaliação local". A Destination confirmada deste Map não cita a comparação, então a primeira decisão é se ela entra (e a Destination muda) ou vai para Out of scope.

Evidência relevante: o topic-vector-index-hosting carrega só o caso 1 na AWS e mantém o Bedrock em us-east-1.
