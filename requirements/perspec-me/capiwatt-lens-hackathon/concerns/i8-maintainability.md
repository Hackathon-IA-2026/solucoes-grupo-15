---
concern_id: i8-maintainability
concern: ~/.claude/skills/perspec-me/catalog/concerns/i8-maintainability/README.md
perspective: infrastructure
status: partial
topics:
  - issue-15 — O backend (F3) deve ser dono também do armazenamento documental, junto das arestas, para que grafo e leitura de documentos não atravessem HTTP, dado um corpus da ordem de 100 documentos?
updated_at: 2026-09-18
---

## Current resolution

O que a manutenibilidade exige neste projeto é **o port trocável e a separação de desenvolvimento F2/F3**, não a fronteira HTTP em si (decisão de Eduardo, 2026-09-18, issue-15). Consequências:

- A troca de Bedrock/OpenSearch por outro embedder/índice (ou a entrada de Neptune para o grafo) toca **um** lugar cada: o adapter atrás do port `VectorService` no `ai`, ou o repositório de relações atrás da interface própria no backend ([[i4-storage]], [[i9-integration]]). Nenhuma troca exige mover dados entre módulos, porque o índice é derivado e reconstruível.
- A divisão "catálogo no backend / índice derivado no `ai`" reduz o que precisa ser mantido em sincronia entre módulos a dois atributos de filtro (`family_id`, `document_version`) com uma regra única de reconciliação: `reindex`.
- Escala do corpus (~100 documentos — número superado pela issue-11: são 10 PDFs, [[d16-golden-dataset]]; e, de todo modo, só o corpus de avaliação, [[i4-storage]]) não impõe nenhuma decisão de manutenibilidade no primeiro ciclo; um crescimento por ingestão contínua (Fog) muda store físico (#8), não a divisão de responsabilidades.

## Confirmed facts

- Reunião 2026-09-17 (Map #1, Notes): arquitetura limpa em todos os módulos; interface do serviço vetorial separada da implementação Bedrock para troca futura.
- Plano (linhas 96–102): três módulos com Dockerfile próprio; "a separação em três módulos é uma separação de desenvolvimento; um módulo pode gerar mais de uma função" Lambda.
- Nada em `hackathon/` implementado em 2026-09-18 — a revisão de issue-2/issue-4 custou só re-registro.

## Decisions

- 2026-09-18 (issue-15): manutenibilidade é garantida pelo port trocável + índice derivado, não por HTTP entre módulos; merger total (um só deployable) rejeitado.

## Derived requirements and constraints

- Trocar embedder/índice = trocar adapter no `ai` + `reindex`; trocar store de grafo = trocar repositório no backend. Nenhuma das duas atravessa a fronteira.
- Testes de contrato do port (issue-2) continuam a ser a prova de que a troca não quebra o backend.

## Open questions

- Como um `reindex` completo é disparado e acompanhado em produção (job de ingestão? operação administrativa?) — provável desdobramento da issue #8 ou #9.

## Evidence

- Map issue #1, Notes; `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 96–104, 132–133.

## Topic history

- issue-15: primeiro toque — fixou que a exigência de manutenibilidade é o port trocável e o índice derivado, não a fronteira HTTP; rejeitou o merger total.
