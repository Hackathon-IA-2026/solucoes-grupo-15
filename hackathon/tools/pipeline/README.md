# Pipeline de extração em lote com manifesto único (issue #68)

Prefactor que leva o pipeline PDF → Markdown validado no caso 1 (#59/#60/#61)
para o corpus completo de `hackathon/data/` (`case-1-carolina-mmgd/` + as 5
categorias de `processos aneel/processos/`). Entrega o **manifesto do
corpus**, a **triagem** por `tipo_documento`, o **contrato de rota** (ver
`requirements/contracts/extraction-route.md`) e o **executor em lote
retomável**, com quatro rotas já implementadas: PDF com camada de texto e
regras genéricas (#68), HTML nativo do SEI (#70), PDF com specs de
filtragem geradas por LLM (#71) e PDF escaneado/página escaneada → OCR ou
visão (#72). Só uma rota por formato fica registrada em
`cli.py::build_registry()` — para `pdf`, é `PdfOcrRoute` (#72), que chama
`PdfLlmSpecRoute` (#71) diretamente por composição; ver
`requirements/contracts/extraction-route.md`, seção "Ponto de extensão".

## Módulos

| Módulo | Responsabilidade |
| --- | --- |
| `manifest.py` | Varre as duas fontes do corpus, expande ZIPs recursivamente, calcula `corpus_version` (hash determinístico da identidade dos documentos). |
| `triage.py` | Marca como descartado, antes de qualquer extração, todo documento cujo `tipo_documento`/formato não tem valor de busca. **Lista sujeita à aprovação de Eduardo** — ver o próprio módulo. |
| `routes/` | Contrato de rota (`ExtractionRoute`/`ExtractionResult`/`RouteRegistry`) e as rotas concretas: `pdf_text_generic.py` (#68, reaproveitando o extrator do protótipo da #59), `html_sei.py` (#70, HTML nativo do SEI → Markdown via BeautifulSoup+lxml), `pdf_llm_spec.py` (#71, spec de filtragem por documento gerada por Bedrock) e `pdf_ocr.py` (#72, detecção por página + OCR/visão via Bedrock para páginas escaneadas). |
| `executor.py` | Despacha cada documento não descartado para uma rota pelo formato, com cache por `(sha256, extractor_version)` e relatório por documento. |
| `cli.py` | Linha de comando: `manifest` (gera o manifesto e imprime `corpus_version`) e `run` (executa o lote sobre um recorte do corpus). |
| `scan_corpus_report.py` | Script avulso (#72): roda só a detecção por página de `pdf_ocr.py` (sem OCR real, sem custo) sobre o manifesto completo e imprime a contagem de documentos/páginas escaneados do corpus — ver o evidence pack da #72 para o resultado. |

## Dependências

`manifest.py`/`triage.py`/`executor.py`/`routes/pdf_text_generic.py` usam só
a stdlib + os binários `pdftotext`/`pdfinfo` (poppler-utils, já presentes no
ambiente). `routes/pdf_ocr.py` (#72) usa também `pdftoppm`/`pdfimages`
(poppler-utils, mesmo pacote) e `boto3` (chamada de visão via Bedrock
Converse, mesma dependência/credenciais da #71 — `source .env` antes de
rodar). `routes/html_sei.py` (issue #70) precisa de `beautifulsoup4` +
`lxml` — instale com:

```bash
python3.12 -m pip install -r hackathon/tools/pipeline/requirements.txt
```

## Uso

```bash
# gera o manifesto completo e imprime corpus_version + resumo da triagem
python3.12 hackathon/tools/pipeline/cli.py manifest

# roda o executor sobre uma categoria inteira (retomável: uma segunda
# chamada não reprocessa nada que já esteja em cache)
python3.12 hackathon/tools/pipeline/cli.py run --categoria "04 Compartilhamento de postes"

# roda sobre o corpus do caso 1
python3.12 hackathon/tools/pipeline/cli.py run --corpus-id case-1-carolina-mmgd
```

Saída (manifesto, cache de extração, Markdown gerado, relatórios) vai para
`hackathon/.pipeline-output/` — fora do git, como o próprio corpus (ver
`hackathon/data/processos aneel/README.md`); storage externo permanece em
aberto em outra issue (I4).

## Testes

```bash
python3.12 -m pytest hackathon/tools/pipeline -q
```

Todos os testes usam corpora sintéticos sob `tmp_path` (`test_manifest.py`,
`test_triage.py`, `test_executor.py`), PDFs gerados on-the-fly com
`weasyprint` (`test_routes_pdf_text_generic.py`, `test_routes_pdf_llm_spec.py`,
`test_routes_pdf_ocr.py` — as duas últimas com um `GenerateFn`/`OcrFn` falso
no lugar da chamada real ao Bedrock) ou fixtures HTML sintéticas inline
(`test_routes_html_sei.py`) — nenhum depende do corpus real (gitignored,
~3,3 GB). A validação com o corpus real (piloto de custo/qualidade, página
24 de `recurso-48500.000639-2019-07.pdf`, contagem de páginas escaneadas)
está registrada nos evidence packs das issues #71/#72, não nesta suíte.
