---
concern_id: d1-source
concern: ~/.claude/skills/perspec-me/catalog/concerns/d1-source/README.md
perspective: data
status: resolved
topics:
  - issue-10 — Quais tipos de documento compõem o caso 1 e quais metadados cada um precisa carregar?
updated_at: 2026-09-22
---

## Current resolution

O corpus inicial do caso 1 é a entrega da Carolina guardada em `hackathon/data/case-1-carolina-mmgd/`: 10 PDFs organizados por NUP e acompanhados de um README com inventário, contexto e regra de acesso. A entrega é o canal de aquisição; Eduardo confirmou em 2026-09-22 que a origem oficial dos documentos é o SEI/ANEEL. Identificadores Sicnet/SIC encontrados nos PDFs permanecem como identificadores legados da peça, não como a origem atual do corpus.

Processos anteriores que continuaram no SEI em 2025 podem receber `9` no sexto dígito do NUP, portanto o identificador anterior e o NUP corrente precisam ser preservados como aliases do mesmo processo. A data de coleta e o localizador concreto de cada arquivo serão preenchidos na ingestão sem reabrir a decisão sobre a origem.

A cópia de `recurso-48500.000639-2019-07.pdf` pode ser exposta: Carolina liberou expressamente o arquivo, conforme confirmação de Eduardo em 2026-09-22. A inscrição histórica `CLASSIFICAÇÃO: Reservada` continua preservada como metadado encontrado no documento e a autorização de exposição fica registrada separadamente, com sua autoridade e data.

## Confirmed facts

- Eduardo informou em 2026-09-22 que a issue #10 foi concluída e indicou `hackathon/data/case-1-carolina-mmgd/` como local dos documentos.
- O diretório contém 10 PDFs, distribuídos entre três precedentes priorizados: `48500.004024/2017-80`, `48500.000639/2019-07` e `48500.901433/2024-53`, com dois NUPs documentais adicionais ligados ao caso Coelba.
- O README da entrega define a virada de consulta Sicnet2 → SEI e a regra do sexto dígito `9` para processos antigos que continuaram em 2025.
- Os PDFs têm texto extraível, não estão criptografados e carregam identificadores oficiais no conteúdo, como NUP, número do documento SEI/Sicnet, número de auto, carta ou voto e código de verificação quando aplicável.
- O recurso da CEMIG mostra `CLASSIFICAÇÃO: Reservada`, apesar de a entrega declarar os documentos públicos.
- Eduardo confirmou em 2026-09-22 que todos os documentos entregues têm origem no SEI/ANEEL.
- Eduardo confirmou em 2026-09-22 que Carolina liberou a exposição da cópia do recurso da CEMIG.

## Decisions

- 2026-09-22 (issue-10): a entrega versionada no repositório é o corpus de entrada do primeiro ciclo e deve preservar a proveniência da entrega sem confundi-la com a fonte oficial do documento.
- 2026-09-22 (issue-10): `official_source_system = sei_aneel` para os documentos entregues; identificadores Sicnet/SIC permanecem como identificadores legados quando encontrados.
- 2026-09-22 (issue-10): a cópia do recurso da CEMIG pode ser exposta por liberação da Carolina; a marca histórica `Reservada` não é apagada e convive com o registro da autorização.

## Derived requirements and constraints

- Cada versão documental deve registrar `acquisition_channel`, `repository_path`, `collected_at`, `checksum`, `page_count`, `text_extraction_status`, `official_source_system`, `official_source_locator`, `official_document_id`, `process_number_display`, `process_number_normalized` e `process_number_aliases`.
- Para esta entrega, `official_source_system` deve ser `sei_aneel`; identificadores provenientes de Sicnet/SIC devem ser guardados em `legacy_identifiers` quando presentes.
- O NUP anterior e o NUP ajustado com sexto dígito `9` devem resolver para o mesmo nó de processo sem apagar a forma impressa em cada documento.
- A ingestão deve guardar separadamente `embedded_access_marking`, `exposure_status`, `exposure_authority` e `exposure_authorized_at`, sem apagar divergências históricas.
- Localizadores e identificadores oficiais devem continuar disponíveis mesmo quando o arquivo foi adquirido por entrega manual.

## Open questions

- Nenhuma questão material permanece para a Destination atual. Localizador e data de coleta são dados operacionais a preencher na ingestão.

## Evidence

- `hackathon/data/case-1-carolina-mmgd/README.md` — fontes, regra de migração de NUP, inventário dos PDFs e pendências de proveniência.
- Os 10 PDFs sob `hackathon/data/case-1-carolina-mmgd/`, inspecionados em 2026-09-22; o cabeçalho do recurso CEMIG contém a divergência de classificação.

## Topic history

- issue-10: fixou o corpus entregue como entrada do primeiro ciclo, confirmou o SEI/ANEEL como origem e autorizou a exposição da cópia marcada historicamente como reservada, preservando proveniência e marca de acesso como metadados distintos.
