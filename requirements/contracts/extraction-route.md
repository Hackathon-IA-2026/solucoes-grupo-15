---
contract: manifesto/executor ↔ rotas de extração
sources:
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/d14-data-operations-modeling.md
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/i7-reproducibility.md
  - hackathon/tools/prototypes/pdf_to_markdown/README.md
last_synced_with_sources: 2026-09-26 (issue-68)
---

# Contrato de fronteira: manifesto/executor ↔ rotas de extração

Snapshot legível do contrato entre o executor em lote (`hackathon/tools/pipeline/executor.py`, issue #68) e as rotas de extração que outras issues plugam nele: a rota PDF-com-texto genérica desta própria issue (`routes/pdf_text_generic.py`), e as rotas futuras de HTML (#70), PDF com specs geradas por LLM (#71) e OCR (#72). **A fonte de verdade do contrato é o código** (`hackathon/tools/pipeline/routes/__init__.py`, docstring do módulo) — este arquivo é um resumo derivado dele, para quem for implementar #70/#71/#72 sem precisar ler o executor inteiro primeiro.

> **Manutenção:** este arquivo deve ser atualizado sempre que `routes/__init__.py` mudar de forma a afetar a interface `ExtractionRoute`/`ExtractionResult`, ou quando D14 (extração por IA) ou I7 (reprodutibilidade/`corpus_version`) mudarem de forma a afetar esta fronteira. Ver seção "Como manter em sincronia" no fim.

## Divisão de posse

- **`manifest.py`** (issue #68) é dono do **manifesto do corpus**: um registro (`ManifestDocument`) por documento das duas fontes (`case-1-carolina-mmgd/` e `processos aneel/processos/<categoria>/`), com ZIPs já expandidos em documentos próprios (`origem` registra a proveniência). Também é dono do `corpus_version` — hash determinístico dos campos de identidade do documento (nunca da decisão de triagem, nunca de metadados voláteis como a URL de consulta do SEI).
- **`triage.py`** (issue #68) é dono da **triagem por `tipo_documento`**: decide, antes de qualquer extração, quais documentos são descartados por não terem valor de busca (lista em `DISCARD_TIPOS`/`DISCARD_FORMATOS`, aprovada por Eduardo — ver o próprio módulo).
- **`executor.py`** (issue #68) é dono do **despacho e do cache**: escolhe a rota pelo formato (`RouteRegistry.dispatch`), materializa o arquivo de origem quando o documento veio de dentro de um ZIP, aplica o cache por `(sha256, extractor_version)` e escreve o relatório por documento.
- **Cada rota** (`routes/pdf_text_generic.py` nesta issue; `routes/html_*.py`, `routes/pdf_llm_spec.py`, `routes/ocr.py` nas issues seguintes) é dona só da **conversão de um formato para Markdown com marcadores de página**. Uma rota nunca sabe de cache, retomada ou relatório — isso é do executor.

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
- **Saída**: Markdown com marcadores de página `<!-- page:N -->` antes do conteúdo de cada página — mesmo formato que `hackathon/tools/prototypes/pdf_to_markdown/filter_verbatim.py` já escreve (issue #59). Uma rota sem noção natural de página (HTML, issue #70) deve documentar, no próprio docstring do módulo, o que ela preenche nesse marcador único (ex.: `<!-- page:1 -->` para o documento inteiro).
- **Identidade da versão extraída**: `(sha256, extractor_version)`. Uma rota deve trocar sua própria `extractor_version` sempre que sua saída para a mesma entrada mudaria (nova regex, nova dependência com saída diferente etc.) — o cache do executor nunca deve servir uma entrada antiga silenciosamente.
- **Cópia verbatim (D14)**: nenhuma rota pode reescrever ou resumir frase alguma — só remover linhas/blocos (assinatura, certificação, boilerplate) por regra explícita e auditável. Isso vale para todas as rotas presentes e futuras, não só para a rota PDF genérica desta issue.

## Ponto de extensão para as issues #70/#71/#72

Plugar uma nova rota é: implementar `ExtractionRoute` (uma classe com `name`, `extractor_version`, `can_handle`, `extract`) num novo módulo em `routes/`, e registrá-la em `cli.py::build_registry()`. Nenhuma mudança no executor é esperada:

- **#70 (HTML nativo do SEI)**: `can_handle` responde `True` para `formato == "html"`; a rota decide e documenta o que preenche no marcador de página único.
- **#71 (PDF com specs geradas por LLM)**: mesma família de formato (`pdf`) da rota desta issue — para não colidir, `#71` deve registrar sua rota **antes** da rota genérica em `build_registry()` (primeira que responder `can_handle` vence) e sua própria rota decide, internamente, se usa a spec gerada por LLM ou devolve `pending` para a rota genérica tratar (ou vice-versa — a ordem exata de precedência entre as duas rotas de PDF é decisão da #71, não desta issue).
- **#72 (OCR)**: hoje, `routes/pdf_text_generic.py` já detecta "PDF sem camada de texto" e devolve `status="pending"` com uma mensagem apontando para a #72 — a rota de OCR pode assumir esses documentos registrando-se como uma rota adicional para `formato == "pdf"` que roda depois da rota de texto, tratando especificamente o caso em que a rota de texto devolveu `pending` por falta de texto (mecanismo exato de encadeamento é decisão da #72).

## Como manter em sincronia

1. Toda mudança na interface `ExtractionRoute`/`ExtractionResult` nasce no código (`routes/__init__.py`), nunca direto aqui.
2. Depois de mudar o código, atualize este arquivo para refletir o estado vigente.
3. Atualize `last_synced_with_sources` no frontmatter para a data do refresh.
4. Se uma revisão de D14 ou I7 nas Concern Resolution pages afetar esta fronteira (ex.: novo campo obrigatório no marcador de página, nova regra de verbatim), revise este arquivo na mesma sessão.
