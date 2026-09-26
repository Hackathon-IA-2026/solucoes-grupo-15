# Pipeline de extração em lote com manifesto único (issue #68)

Prefactor que leva o pipeline PDF → Markdown validado no caso 1 (#59/#60/#61)
para o corpus completo de `hackathon/data/` (`case-1-carolina-mmgd/` + as 5
categorias de `processos aneel/processos/`). Entrega o **manifesto do
corpus**, a **triagem** por `tipo_documento`, o **contrato de rota** (ver
`requirements/contracts/extraction-route.md`) e o **executor em lote
retomável** — com a primeira rota (PDF com camada de texto, regras
genéricas). As rotas de HTML (#70), PDF com specs geradas por LLM (#71) e
OCR (#72) são tickets independentes que plugam nesse mesmo contrato.

## Módulos

| Módulo | Responsabilidade |
| --- | --- |
| `manifest.py` | Varre as duas fontes do corpus, expande ZIPs recursivamente, calcula `corpus_version` (hash determinístico da identidade dos documentos). |
| `triage.py` | Marca como descartado, antes de qualquer extração, todo documento cujo `tipo_documento`/formato não tem valor de busca. **Lista sujeita à aprovação de Eduardo** — ver o próprio módulo. |
| `routes/` | Contrato de rota (`ExtractionRoute`/`ExtractionResult`/`RouteRegistry`) e a primeira rota concreta (`pdf_text_generic.py`, reaproveitando o extrator do protótipo da #59). |
| `executor.py` | Despacha cada documento não descartado para uma rota pelo formato, com cache por `(sha256, extractor_version)` e relatório por documento. |
| `cli.py` | Linha de comando: `manifest` (gera o manifesto e imprime `corpus_version`) e `run` (executa o lote sobre um recorte do corpus). |

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
`test_triage.py`, `test_executor.py`) ou PDFs gerados on-the-fly com
`weasyprint` (`test_routes_pdf_text_generic.py`) — nenhum depende do corpus
real (gitignored, ~3,3 GB).
