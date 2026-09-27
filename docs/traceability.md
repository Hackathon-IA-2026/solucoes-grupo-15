# Rastreabilidade: resultado, fonte e decisão

## Da resposta à peça de origem

O [contrato de busca](../requirements/contracts/frontend-backend.md) e a [rota pública](../hackathon/backend/app/routes/search.py) devolvem cada resultado como um **chunk**, com `processo_numero`, `document_id`, `document_version`, `chunk_id`, `chunk_index`, `excerpt` e `localizador`. O [frontend](../hackathon/frontend/src/services/appRepository.ts) agrupa esses trechos por processo para exibir o ranking. A [rota de documentos](../hackathon/backend/app/routes/documents.py) expõe a versão e, quando presente, o PDF de origem do caso 1. Assim, o caminho auditável é: **card → trecho identificado → versão documental → processo SEI/Sicnet → PDF/Markdown de origem**. Um `localizador` pode ser nulo; nesse caso, os identificadores e o excerto continuam disponíveis, mas o salto para o texto extraído não é garantido.

Os [PDFs e Markdown do caso 1](../hackathon/data/case-1-carolina-mmgd/README.md) estão versionados. Para o [corpus maior da ANEEL](../hackathon/data/processos%20aneel/README.md), apenas manifestos de proveniência estão no Git; os arquivos completos excedem os limites de tamanho e ainda aguardam armazenamento externo definido. Portanto, a rastreabilidade do caso 1 é mais completa que a do corpus total.

## Da execução e da decisão ao registro

A [resposta da busca](../hackathon/backend/app/routes/search.py) inclui `request_id`, `corpus_version`, `model_version`, `ranking_version` e `stale_corpus`. O [pipeline de manifesto](../hackathon/tools/pipeline/README.md) define a identidade/versionamento do corpus; o [replay](../hackathon/backend/app/replay.py) e a [suíte e2e](../hackathon/tests_e2e/README.md) verificam parte da reprodutibilidade. O [resultado medido](../hackathon/tools/case1_recall/output/results.json) preserva consulta, modelo, corpus e ranking para o caso 1.

Decisões de produto e infraestrutura são registradas em [issues](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues), [ADRs](../hackathon/docs/adr/) e [Resolution pages por Concern](../requirements/perspec-me/). Os [contratos](../requirements/contracts/) são snapshots dessas resoluções. [Evidence packs](evidence-packs.md) ligam critérios de aceite a comandos e resultados, com falhas e verificações não executadas explicitadas.
