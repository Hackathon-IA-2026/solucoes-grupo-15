---
concern_id: m10-versioning
concern: /home/eduardo/.agents/skills/perspec-me/catalog/concerns/m10-versioning/README.md
perspective: model
status: resolved
topics:
  - issue-9 — Como corpus_version, model_version e ranking_version são registrados para reproduzir uma execução?
updated_at: 2026-09-18
---

## Current resolution

As três versões identificam registros imutáveis do corpus, modelo e ranking efetivamente usados. O módulo `ai` informa esses identificadores e fornece os artefatos; o backend registra a entrada efetiva, as versões, o vetor da consulta, a resposta ordenada e a referência ao código e ambiente com dependências fixadas. Preservar os embeddings permite reexecutar as buscas registradas sem AWS. Fixtures exigem igualdade dos resultados e da ordem; diferenças na busca real são registradas e comparadas. Resolvido para o primeiro ciclo do hackathon, com aceite de Eduardo em 2026-09-18.

## Confirmed facts

- O plano exige `request_id`, `data_mode`, `corpus_version`, `model_version` e `ranking_version` na resposta da busca.
- A issue-8 registra o ambiente AWS temporário e a execução local como base de reprodutibilidade.
- 2026-09-18 (Eduardo): reexecução sem AWS, igualdade nas fixtures e retenção proposta dos corpora foram confirmadas.
- 2026-09-18 (Eduardo): "aceito as sugestões" confirmou o contrato abaixo e o encerramento do Topic.

## Decisions

- Preservar cada versão de corpus usada em avaliação ou demonstração até o encerramento do hackathon; versões intermediárias sem evidência associada podem ser descartadas.
- Fixtures devem preservar resultados e ordem entre execuções da mesma versão.
- `corpus_version` identifica uma publicação imutável de documentos, metadados, famílias, chunks e embeddings.
- `model_version` identifica provedor, modelo, região e parâmetros usados para gerar embeddings.
- `ranking_version` identifica código e configuração da recuperação, filtros, pesos, agrupamento e desempate.
- O backend registra `request_id`, `data_mode`, entrada efetiva, as três versões, vetor da consulta, resposta ordenada e referência ao código e ambiente. O módulo `ai` fornece as versões e os artefatos efetivamente usados.
- Registrar commit Git e dependências fixadas, incluindo versões das imagens do ambiente local, para recuperar código e ambiente da execução preservada.
- Na busca real, registrar e comparar diferenças, sem exigir igualdade exata; a qualidade contra o gabarito é tratada na issue-11.

## Derived requirements and constraints

- Identificadores de versão precisam continuar resolvendo para os artefatos necessários à reexecução durante o prazo de retenção.
- Embeddings reais de documentos e consultas registrados precisam sobreviver ao término do acesso à AWS.
- Uma alteração no conteúdo identificado exige nova versão; o mesmo identificador não pode apontar para configurações ou artefatos diferentes.
- A retenção inclui os artefatos e configurações referenciados pelas execuções de avaliação e demonstração, até o encerramento do hackathon.
- Reexecutar offline usa os vetores preservados para executar novamente a recuperação e o ranking; perguntas novas podem continuar exigindo Bedrock.

## Open questions

- Nenhuma pendência para a issue-9 no primeiro ciclo. A estratégia concreta de chunking e embeddings pertence à issue-13; este contrato registra a configuração que vier a ser escolhida.

## Evidence

- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md`, linhas 111, 118, 155 e 177.
- `i7-reproducibility.md`, decisões da issue-8 e primeira rodada da issue-9.
- Sessão perspec-me da issue-9, resposta de Eduardo em 2026-09-18: "1. reexecutar sem aws 2. igualdade nas fixtures 3. podemos sim".
- Sessão perspec-me da issue-9, aceite final de Eduardo em 2026-09-18: "aceito as sugestões".

## Topic history

- issue-9: definiu registros imutáveis de corpus, modelo e ranking, registro da execução e ambiente, retenção e reexecução sem AWS; Topic encerrado com aceite de Eduardo.
