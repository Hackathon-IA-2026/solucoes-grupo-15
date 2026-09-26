---
contract: manifesto/executor ↔ rotas de extração
sources:
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/d14-data-operations-modeling.md
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/i7-reproducibility.md
  - hackathon/tools/prototypes/pdf_to_markdown/README.md
last_synced_with_sources: 2026-09-26 (issue-71)
---

# Contrato de fronteira: manifesto/executor ↔ rotas de extração

Snapshot legível do contrato entre o executor em lote (`hackathon/tools/pipeline/executor.py`, issue #68) e as rotas de extração que outras issues plugam nele: a rota PDF-com-texto genérica (`routes/pdf_text_generic.py`, issue #68), a rota de HTML nativo do SEI (`routes/html_sei.py`, issue #70) e a rota de PDF com specs de filtragem geradas por LLM (`routes/pdf_llm_spec.py`, issue #71) já implementadas, e a rota futura de OCR (#72). **A fonte de verdade do contrato é o código** (`hackathon/tools/pipeline/routes/__init__.py`, docstring do módulo) — este arquivo é um resumo derivado dele, para quem for implementar #72 sem precisar ler o executor inteiro primeiro.

> **Manutenção:** este arquivo deve ser atualizado sempre que `routes/__init__.py` mudar de forma a afetar a interface `ExtractionRoute`/`ExtractionResult`, ou quando D14 (extração por IA) ou I7 (reprodutibilidade/`corpus_version`) mudarem de forma a afetar esta fronteira. Ver seção "Como manter em sincronia" no fim.

## Divisão de posse

- **`manifest.py`** (issue #68) é dono do **manifesto do corpus**: um registro (`ManifestDocument`) por documento das duas fontes (`case-1-carolina-mmgd/` e `processos aneel/processos/<categoria>/`), com ZIPs já expandidos em documentos próprios (`origem` registra a proveniência). Também é dono do `corpus_version` — hash determinístico dos campos de identidade do documento (nunca da decisão de triagem, nunca de metadados voláteis como a URL de consulta do SEI).
- **`triage.py`** (issue #68) é dono da **triagem por `tipo_documento`**: decide, antes de qualquer extração, quais documentos são descartados por não terem valor de busca (lista em `DISCARD_TIPOS`/`DISCARD_FORMATOS`, aprovada por Eduardo — ver o próprio módulo).
- **`executor.py`** (issue #68) é dono do **despacho e do cache**: escolhe a rota pelo formato (`RouteRegistry.dispatch`), materializa o arquivo de origem quando o documento veio de dentro de um ZIP, aplica o cache por `(sha256, extractor_version)` e escreve o relatório por documento.
- **Cada rota** (`routes/pdf_text_generic.py`, `routes/html_sei.py`, `routes/pdf_llm_spec.py` já implementadas; `routes/ocr.py` na issue seguinte) é dona só da **conversão de um formato para Markdown com marcadores de página**. Uma rota nunca sabe de cache, retomada ou relatório do executor — isso é do executor. A única exceção documentada é `routes/pdf_llm_spec.py` (#71): ela mantém seu **próprio** cache de spec gerada por LLM (não o cache do executor), content-addressed por hash do texto bruto extraído — ver "Ponto de extensão" abaixo.

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

## Ponto de extensão para a issue #72

Plugar uma nova rota é: implementar `ExtractionRoute` (uma classe com `name`, `extractor_version`, `can_handle`, `extract`) num novo módulo em `routes/`, e registrá-la em `cli.py::build_registry()`. Nenhuma mudança no executor é esperada:

- **#70 (HTML nativo do SEI) — implementada** (`routes/html_sei.py`): `can_handle` responde `True` para `formato == "html"`. Usa BeautifulSoup+lxml (nova dependência do módulo — ver `hackathon/tools/pipeline/requirements.txt`) para andar a árvore DOM em vez de regex sobre HTML bruto; remove o bloco de assinatura/CRC do SEI por marcador estrutural (`<div unselectable="on">`, verificado 100% consistente nos 612 HTML reais do corpus) e a tabela de referência de rodapé por casamento textual exato — nunca por posição isolada nem por rewrite de frase. Ver o docstring do módulo para o detalhamento completo das regras de remoção (auditáveis) e uma limitação conhecida e documentada (numeração gerada via contador CSS em alguns documentos, invisível a qualquer extrator estático de texto — fora de escopo da #70).
- **#71 (PDF com specs geradas por LLM) — implementada** (`routes/pdf_llm_spec.py`): mesma família de formato (`pdf`) da `routes/pdf_text_generic.py` (#68) — **decisão de precedência tomada pela #71**: `PdfLlmSpecRoute` é a *única* rota para `formato == "pdf"` registrada em `build_registry()` (`PdfTextGenericRoute` não é registrada ali — ficaria permanentemente inatingível, já que `RouteRegistry.dispatch` usa a primeira `can_handle` que casar). `PdfLlmSpecRoute.extract()` reutiliza as próprias funções de `pdf_text_generic.py` (extração mecânica `pdftotext -layout` + heurística de "sem camada de texto") e cai internamente no filtro genérico (sem spec por documento) quando: (a) não há camada de texto extraível (candidato à #72, não uma questão de spec LLM); ou (b) a chamada ao Bedrock falha ou devolve algo que não passa validação de forma — nunca por um segundo `RouteRegistry.dispatch`. `PdfTextGenericRoute` continua existindo e testada isoladamente (`test_routes_pdf_text_generic.py`) como o comportamento de fallback que a #71 chama internamente, só não como uma segunda entrada no registry. A rota mantém seu próprio cache de spec, content-addressed por `sha256(texto_bruto) + versão_do_prompt + model_id` (nunca pelo `extractor_version` do executor, que é global à rota) — ver o docstring de `routes/pdf_llm_spec.py`, seção "Two-tier cache", para o detalhamento de como isso garante que regerar a spec de um documento invalida só o cache daquele documento.
- **#72 (OCR)**: hoje, tanto `routes/pdf_text_generic.py` quanto `routes/pdf_llm_spec.py` detectam "PDF sem camada de texto" (mesma heurística: caracteres não-brancos por página abaixo de `MIN_CHARS_PER_PAGE`) e devolvem `status="pending"` com uma mensagem apontando para a #72 — a rota de OCR pode assumir esses documentos registrando-se como uma rota adicional para `formato == "pdf"` que roda depois de `PdfLlmSpecRoute` (que continuará sendo a primeira a responder `can_handle` para `pdf`), tratando especificamente o caso em que ela devolveu `pending` por falta de texto (mecanismo exato de encadeamento é decisão da #72).

## Como manter em sincronia

1. Toda mudança na interface `ExtractionRoute`/`ExtractionResult` nasce no código (`routes/__init__.py`), nunca direto aqui.
2. Depois de mudar o código, atualize este arquivo para refletir o estado vigente.
3. Atualize `last_synced_with_sources` no frontmatter para a data do refresh.
4. Se uma revisão de D14 ou I7 nas Concern Resolution pages afetar esta fronteira (ex.: novo campo obrigatório no marcador de página, nova regra de verbatim), revise este arquivo na mesma sessão.
