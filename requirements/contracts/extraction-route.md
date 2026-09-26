---
contract: manifesto/executor ↔ rotas de extração
sources:
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/d14-data-operations-modeling.md
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/i7-reproducibility.md
  - hackathon/tools/prototypes/pdf_to_markdown/README.md
last_synced_with_sources: 2026-09-26 (issue-72)
---

# Contrato de fronteira: manifesto/executor ↔ rotas de extração

Snapshot legível do contrato entre o executor em lote (`hackathon/tools/pipeline/executor.py`, issue #68) e as rotas de extração que outras issues plugam nele: a rota PDF-com-texto genérica (`routes/pdf_text_generic.py`, issue #68), a rota de HTML nativo do SEI (`routes/html_sei.py`, issue #70), a rota de PDF com specs de filtragem geradas por LLM (`routes/pdf_llm_spec.py`, issue #71) e a rota de OCR/visão para PDF escaneado (`routes/pdf_ocr.py`, issue #72) — todas já implementadas. **A fonte de verdade do contrato é o código** (`hackathon/tools/pipeline/routes/__init__.py`, docstring do módulo) — este arquivo é um resumo derivado dele.

> **Manutenção:** este arquivo deve ser atualizado sempre que `routes/__init__.py` mudar de forma a afetar a interface `ExtractionRoute`/`ExtractionResult`, ou quando D14 (extração por IA) ou I7 (reprodutibilidade/`corpus_version`) mudarem de forma a afetar esta fronteira. Ver seção "Como manter em sincronia" no fim.

## Divisão de posse

- **`manifest.py`** (issue #68) é dono do **manifesto do corpus**: um registro (`ManifestDocument`) por documento das duas fontes (`case-1-carolina-mmgd/` e `processos aneel/processos/<categoria>/`), com ZIPs já expandidos em documentos próprios (`origem` registra a proveniência). Também é dono do `corpus_version` — hash determinístico dos campos de identidade do documento (nunca da decisão de triagem, nunca de metadados voláteis como a URL de consulta do SEI).
- **`triage.py`** (issue #68) é dono da **triagem por `tipo_documento`**: decide, antes de qualquer extração, quais documentos são descartados por não terem valor de busca (lista em `DISCARD_TIPOS`/`DISCARD_FORMATOS`, aprovada por Eduardo — ver o próprio módulo).
- **`executor.py`** (issue #68) é dono do **despacho e do cache**: escolhe a rota pelo formato (`RouteRegistry.dispatch`), materializa o arquivo de origem quando o documento veio de dentro de um ZIP, aplica o cache por `(sha256, extractor_version)` e escreve o relatório por documento.
- **Cada rota** (`routes/pdf_text_generic.py`, `routes/html_sei.py`, `routes/pdf_llm_spec.py`, `routes/pdf_ocr.py` — todas já implementadas) é dona só da **conversão de um formato para Markdown com marcadores de página**. Uma rota nunca sabe de cache, retomada ou relatório do executor — isso é do executor. Duas rotas mantêm seu **próprio** cache adicional (não o cache do executor), content-addressed: `routes/pdf_llm_spec.py` (#71, cache de spec gerada por LLM, por documento) e `routes/pdf_ocr.py` (#72, cache de texto OCR/visão, por página) — ver "Ponto de extensão" abaixo.

## Forma do boundary

Uma interface Python só (`ExtractionRoute`, um `Protocol` em `routes/__init__.py`) dentro do mesmo processo — sem HTTP, sem serialização entre módulos, porque manifesto/executor/rotas rodam como um único script de linha de comando (`cli.py`), não como serviços separados. `RouteRegistry` mantém a lista ordenada de rotas registradas; o primeiro `can_handle(formato)` que responder `True` vence.

## Operações do port

| Operação | Assinatura |
|---|---|
| `can_handle(formato) -> bool` | Pré-checagem barata, só pelo formato (`ManifestDocument.formato`) — nunca exige fazer a extração para responder. |
| `extract(source_path, out_path) -> ExtractionResult` | Único ponto de trabalho real da rota. |

### `ExtractionResult`

| Campo | Significado |
|---|---|
| `status` | `"extracted"` (Markdown escrito em `out_path`), `"pending"` (razão legítima e documentada para não ter extraído — formato sem rota, PDF sem camada de texto, documento restrito) ou `"error"` (a rota deveria ter processado e falhou inesperadamente). |
| `extractor_version` | Identifica a versão da rota — junto com `sha256`, é a chave de cache do executor. |
| `markdown_path` | Preenchido só quando `status == "extracted"`. |
| `pages_total` / `pages_kept` / `percent_removed` | Insumo do relatório por documento (issue #68, critério de aceite). |
| `message` | Obrigatório quando `status` é `"pending"` ou `"error"` — nunca um resultado silencioso. |

## Entrada, saída e marcadores de página

- **Entrada**: um `ManifestDocument` com `caminho` real em disco. O executor nunca chama uma rota para um documento `descartado` (triagem) ou sem `sha256` (ex.: `status_origem == "restrito"`, ANEEL nunca disponibilizou o arquivo).
- **Saída**: Markdown com marcadores de página `<!-- page:N -->` antes do conteúdo de cada página — mesmo formato que `hackathon/tools/prototypes/pdf_to_markdown/filter_verbatim.py` já escreve (issue #59). Uma rota sem noção natural de página (HTML, issue #70) deve documentar, no próprio docstring do módulo, o que ela preenche nesse marcador único (ex.: `<!-- page:1 -->` para o documento inteiro). **Decisão tomada pela #70** (`routes/html_sei.py`): documento HTML inteiro = página única, sempre `<!-- page:1 -->` e `pages_total = pages_kept = 1` — não há mecanismo de descarte de página parcial nessa rota (nada equivalente ao `drop_pages` do protótipo PDF), porque não há unidade de página para descartar; um documento sem conteúdo aproveitável depois de remover o boilerplate é `status="pending"`, nunca uma página "descartada".
- **Identidade da versão extraída**: `(sha256, extractor_version)`. Uma rota deve trocar sua própria `extractor_version` sempre que sua saída para a mesma entrada mudaria (nova regex, nova dependência com saída diferente etc.) — o cache do executor nunca deve servir uma entrada antiga silenciosamente.
- **Cópia verbatim (D14)**: nenhuma rota pode reescrever ou resumir frase alguma — só remover linhas/blocos (assinatura, certificação, boilerplate) por regra explícita e auditável. Isso vale para todas as rotas presentes e futuras, não só para a rota PDF genérica desta issue.

## Ponto de extensão (histórico de decisões #70/#71/#72)

Plugar uma nova rota é: implementar `ExtractionRoute` (uma classe com `name`, `extractor_version`, `can_handle`, `extract`) num novo módulo em `routes/`, e registrá-la em `cli.py::build_registry()`. Nenhuma mudança no executor é esperada:

- **#70 (HTML nativo do SEI) — implementada** (`routes/html_sei.py`): `can_handle` responde `True` para `formato == "html"`. Usa BeautifulSoup+lxml (nova dependência do módulo — ver `hackathon/tools/pipeline/requirements.txt`) para andar a árvore DOM em vez de regex sobre HTML bruto; remove o bloco de assinatura/CRC do SEI por marcador estrutural (`<div unselectable="on">`, verificado 100% consistente nos 612 HTML reais do corpus) e a tabela de referência de rodapé por casamento textual exato — nunca por posição isolada nem por rewrite de frase. Ver o docstring do módulo para o detalhamento completo das regras de remoção (auditáveis) e uma limitação conhecida e documentada (numeração gerada via contador CSS em alguns documentos, invisível a qualquer extrator estático de texto — fora de escopo da #70).
- **#71 (PDF com specs geradas por LLM) — implementada** (`routes/pdf_llm_spec.py`): mesma família de formato (`pdf`) da `routes/pdf_text_generic.py` (#68) — **decisão de precedência tomada pela #71**, depois substituída pela #72 (ver abaixo): à época, `PdfLlmSpecRoute` era a *única* rota para `formato == "pdf"` registrada em `build_registry()`. `PdfLlmSpecRoute.extract()` reutiliza as próprias funções de `pdf_text_generic.py` (extração mecânica `pdftotext -layout` + heurística de "sem camada de texto", aplicada à **média do documento inteiro**) e cai internamente no filtro genérico (sem spec por documento) quando: (a) não há camada de texto extraível pela média do documento (candidato à #72); ou (b) a chamada ao Bedrock falha ou devolve algo que não passa validação de forma — nunca por um segundo `RouteRegistry.dispatch`. A rota mantém seu próprio cache de spec, content-addressed por `sha256(texto_bruto) + versão_do_prompt + model_id` — ver o docstring de `routes/pdf_llm_spec.py`, seção "Two-tier cache". Desde a #72, a lógica de geração/aplicação de spec vive num método próprio, `extract_from_raw_text(raw_text, page_count, out_path)`, chamado tanto pelo próprio `extract()` da #71 quanto pela nova rota da #72 (ver abaixo) — a factoring que tornou essa reutilização possível sem duplicar a lógica de filtragem/LLM.
- **#72 (PDF escaneado → OCR) — implementada** (`routes/pdf_ocr.py`): **nova decisão de precedência** — `PdfOcrRoute` passa a ser a *única* rota registrada para `formato == "pdf"` em `build_registry()` (`PdfLlmSpecRoute` e `PdfTextGenericRoute` deixam de ser alcançáveis pelo registry, mas continuam existindo e testadas isoladamente — mesmo padrão de composição-não-registro que a #71 já havia estabelecido). Motivo: a checagem de "sem camada de texto" das rotas #68/#71 é pela **média do documento inteiro**, o que nunca detecta uma **página individual** escaneada dentro de um documento cuja média fica boa (ex.: página 24 de `recurso-48500.000639-2019-07.pdf` — texto nativo garbled, mas com caracteres suficientes para não disparar a média). `PdfOcrRoute.extract()` faz sua própria extração `pdftotext -layout` página a página e classifica **cada página** por dois sinais independentes (ver docstring do módulo, seção "Detection criterion", para a justificativa completa e as medições reais que fixaram os limiares): (a) densidade de caracteres por página abaixo de `MIN_CHARS_PER_PAGE` (mesma constante da #68/#71, agora aplicada por página); (b) presença de uma imagem raster cobrindo ≥60% da área da própria página (`pdfinfo -f N -l N` + `pdfimages -list`, comparando dimensão física da imagem — pixels/ppi — contra o tamanho em pontos daquela página específica, já que páginas dentro do mesmo PDF podem ter tamanhos diferentes) a ≥150ppi — este é o sinal que cobre o caso da página 24, que o sinal (a) sozinho não cobre. Páginas que disparam qualquer um dos dois sinais são transcritas via **Bedrock Converse com visão** (`us.anthropic.claude-haiku-4-5-20251001-v1:0`, mesmo modelo/região/credenciais da #71); as demais mantêm seu texto nativo inalterado. O texto composto (nativo + OCR/visão, por página) é então passado diretamente a `PdfLlmSpecRoute.extract_from_raw_text(...)` — nunca por um segundo `RouteRegistry.dispatch` — reaproveitando a geração de spec e a filtragem verbatim da #71 sem duplicá-las. Decisão de mecanismo (OCR local `tesseract` vs. modelo com visão): visão via Bedrock, porque o pacote de idioma português do `tesseract` (`tesseract-ocr-por`) não pôde ser instalado neste ambiente (exige `apt-get`/`sudo`, indisponível) e o piloto real contra a página 24 mostrou o `tesseract` em inglês garbling toda acentuação e omitindo a linha de assinatura, enquanto o Bedrock com visão reproduziu a página inteira corretamente acentuada — ver o docstring do módulo e o evidence pack da #72 para a transcrição completa do piloto. A rota mantém seu próprio cache de OCR por página, content-addressed por `sha256(imagem PNG renderizada) + versão_do_prompt + model_id`, registrando também tempo (`elapsed_s`) e custo (`cost_usd`) por página — ver docstring do módulo, seção "Own cache".

## Como manter em sincronia

1. Toda mudança na interface `ExtractionRoute`/`ExtractionResult` nasce no código (`routes/__init__.py`), nunca direto aqui.
2. Depois de mudar o código, atualize este arquivo para refletir o estado vigente.
3. Atualize `last_synced_with_sources` no frontmatter para a data do refresh.
4. Se uma revisão de D14 ou I7 nas Concern Resolution pages afetar esta fronteira (ex.: novo campo obrigatório no marcador de página, nova regra de verbatim), revise este arquivo na mesma sessão.
