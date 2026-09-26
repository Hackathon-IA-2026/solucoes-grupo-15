# Processos ANEEL — dados brutos do baixador SEI

Saída do protótipo de download assistido em lote (#56): documentos públicos
coletados do SEI/ANEEL para as 5 categorias em `processos/`.

## Por que os arquivos não estão neste repositório

O conjunto completo tem ~3,3 GB em 2299 arquivos (1394 PDFs, além de HTML,
JSON, ZIP, imagens e um vídeo), e vários arquivos individuais excedem o
limite de 100 MB por arquivo do GitHub (ex.: `020_SEI_0436146_Processo.pdf`,
180 MB). Por isso, apenas os manifestos `_indice_*.csv` de cada categoria
(nome do arquivo, processo, tipo de documento, data, tamanho em bytes e
status do download) são versionados aqui — o suficiente para auditoria de
proveniência sem violar as restrições do GitHub.

Os documentos originais completos serão disponibilizados em um storage
externo, a definir na resolução da concern [`i4-storage`](../../../requirements/perspec-me/capiwatt-lens-hackathon/concerns/i4-storage.md).
Esta seção será atualizada com o local exato assim que a decisão for
registrada lá.

## Reprodutibilidade

O manifesto de cada categoria pode ser regerado a partir do SEI com o
protótipo de `hackathon/tools/prototypes/document_downloader/` (ver #56).
