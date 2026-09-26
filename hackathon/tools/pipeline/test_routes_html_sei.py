"""Unit tests for routes/html_sei.py (issue #70).

Synthetic HTML fixtures only (same convention as
test_routes_pdf_text_generic.py) — the real corpus is gitignored and not a
dependency of this suite. The fixtures below mirror the exact structure
found by inspecting real SEI HTML files while building this route (see the
module docstring in routes/html_sei.py): a `<div unselectable="on">`
wrapping the "Documento assinado eletronicamente por..." paragraph plus a
QRCode `<img>` and the authenticity/CRC paragraph, followed by an `<hr>`
and a one-row "Referência: Processo..." `<table>`.

Run with: python3.12 -m pytest hackathon/tools/pipeline/test_routes_html_sei.py -q
"""

from __future__ import annotations

from pathlib import Path

from routes.html_sei import EXTRACTOR_VERSION, HtmlSeiRoute

SIGNATURE_BLOCK = """
<div unselectable="on" style="-webkit-user-select:none;user-select:none;">
  <table>
    <tr>
      <td><img alt="Timbre Assinatura" src="data:image/png;base64,AAAA" /></td>
      <td><p>Documento assinado eletronicamente por <b>Fulano de Tal</b>,
      <b>Diretor(a)</b>, em 05/02/2025, &agrave;s 15:06, conforme
      hor&aacute;rio oficial de Bras&iacute;lia.</p></td>
    </tr>
  </table>
  <hr/>
  <table>
    <tr>
      <td><img alt="QRCode Assinatura" src="data:image/png;base64,BBBB" /></td>
      <td><p>A autenticidade deste documento pode ser conferida no site
      https://sei.aneel.gov.br/..., informando o c&oacute;digo verificador
      <b>0041825</b> e o c&oacute;digo CRC <b>6FA95400</b>.</p></td>
    </tr>
  </table>
</div>
<hr style="border-top:medium double #333333;" />
<table style="border-collapse:collapse; width:100%">
  <tbody>
    <tr>
      <td>Refer&ecirc;ncia: Processo n&ordm; 48500.903857/2024-52</td>
      <td>SEI n&ordm; 0041825</td>
    </tr>
  </tbody>
</table>
"""


def _wrap_html(body: str) -> str:
    return (
        '<!DOCTYPE html><html lang="pt-br"><head>'
        '<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />'
        "<title>SEI/ANEEL</title></head><body>" + body + "</body></html>"
    )


def _write_html(tmp_path: Path, body: str, name: str = "doc") -> Path:
    html_path = tmp_path / f"{name}.html"
    html_doc = _wrap_html(body)
    html_path.write_bytes(html_doc.encode("iso-8859-1"))
    return html_path


def test_can_handle_only_html():
    route = HtmlSeiRoute()
    assert route.can_handle("html") is True
    assert route.can_handle("pdf") is False
    assert route.can_handle(None) is False


def test_extracts_verbatim_paragraphs_and_removes_signature_block(tmp_path: Path):
    body = (
        "<p>VOTO</p>"
        "<p>1. Primeiro par&aacute;grafo de conte&uacute;do relevante.</p>"
        "<p>2. Segundo par&aacute;grafo, com uma <b>palavra em negrito</b> no meio.</p>"
        + SIGNATURE_BLOCK
    )
    source = _write_html(tmp_path, body)
    out_path = tmp_path / "out.md"

    result = HtmlSeiRoute().extract(source, out_path)

    assert result.status == "extracted"
    assert result.extractor_version == EXTRACTOR_VERSION
    assert result.route == "html_sei"
    assert result.pages_total == 1
    assert result.pages_kept == 1
    assert result.markdown_path == out_path

    markdown = out_path.read_text(encoding="utf-8")
    assert markdown.startswith("<!-- page:1 -->")
    assert "VOTO" in markdown
    assert "Primeiro parágrafo de conteúdo relevante." in markdown
    assert "Segundo parágrafo, com uma palavra em negrito no meio." in markdown

    # Acceptance criterion: no residual signature/CRC boilerplate.
    lowered = markdown.lower()
    assert "assinado eletronicamente" not in lowered
    assert "código verificador" not in lowered
    assert "código crc" not in lowered
    assert "fulano de tal" not in lowered
    assert "referência: processo" not in lowered
    assert "sei nº 0041825" not in lowered


def test_reports_pending_when_only_boilerplate_remains(tmp_path: Path):
    source = _write_html(tmp_path, SIGNATURE_BLOCK)
    out_path = tmp_path / "out.md"

    result = HtmlSeiRoute().extract(source, out_path)

    assert result.status == "pending"
    assert result.markdown_path is None
    assert not out_path.exists()
    assert "sem conteúdo extraível" in (result.message or "")


def test_preserves_table_as_markdown_including_colspan(tmp_path: Path):
    body = (
        "<table>"
        "<tr><td>Empresa</td><td>Protocolo</td><td>Recomenda&ccedil;&atilde;o</td></tr>"
        '<tr><td colspan="2">GOI&Aacute;S 48500.019112</td><td>Acatar</td></tr>'
        "</table>"
    )
    source = _write_html(tmp_path, body)
    out_path = tmp_path / "out.md"

    result = HtmlSeiRoute().extract(source, out_path)
    assert result.status == "extracted"

    markdown = out_path.read_text(encoding="utf-8")
    lines = [line for line in markdown.splitlines() if line.startswith("|")]
    assert lines[0] == "| Empresa | Protocolo | Recomendação |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| GOIÁS 48500.019112 |  | Acatar |"
    # colspan text kept exactly once — never duplicated across the span.
    assert markdown.count("GOIÁS 48500.019112") == 1


def test_escapes_pipe_characters_inside_table_cells(tmp_path: Path):
    body = "<table><tr><td>a | b</td><td>c</td></tr></table>"
    source = _write_html(tmp_path, body)
    out_path = tmp_path / "out.md"

    result = HtmlSeiRoute().extract(source, out_path)
    assert result.status == "extracted"
    markdown = out_path.read_text(encoding="utf-8")
    assert "a \\| b" in markdown


def test_keeps_reference_looking_text_that_does_not_match_footer_pattern_exactly(
    tmp_path: Path,
):
    # Guardrail against over-matching: a table that merely mentions
    # "Referência" as part of a longer, real sentence must be kept.
    body = (
        "<table><tr><td>Ver a seção "
        "Referência: Processo administrativo e demais anexos citados no "
        "relatório técnico.</td></tr></table>"
    )
    source = _write_html(tmp_path, body)
    out_path = tmp_path / "out.md"

    result = HtmlSeiRoute().extract(source, out_path)
    assert result.status == "extracted"
    markdown = out_path.read_text(encoding="utf-8")
    assert "relatório técnico" in markdown


def test_handles_content_nested_inside_wrapper_divs(tmp_path: Path):
    # Mirrors the real "E-mail" tipo_documento: genuine content sits inside
    # a <div id="conteudo"> wrapper rather than as a direct <body> child.
    body = '<div id="conteudo"><p>Assunto: teste</p><p>Mensagem de e-mail real.</p></div>'
    source = _write_html(tmp_path, body)
    out_path = tmp_path / "out.md"

    result = HtmlSeiRoute().extract(source, out_path)
    assert result.status == "extracted"
    markdown = out_path.read_text(encoding="utf-8")
    assert "Assunto: teste" in markdown
    assert "Mensagem de e-mail real." in markdown


def test_decodes_iso_8859_1_source_into_correct_utf8_output(tmp_path: Path):
    body = "<p>Acentuação: ã, é, ê, ç, õ, ú.</p>"
    source = _write_html(tmp_path, body)
    out_path = tmp_path / "out.md"

    result = HtmlSeiRoute().extract(source, out_path)
    assert result.status == "extracted"
    markdown = out_path.read_text(encoding="utf-8")
    assert "Acentuação: ã, é, ê, ç, õ, ú." in markdown


def test_keeps_content_that_appears_after_the_reference_footer(tmp_path: Path):
    # Mirrors a real pattern (Despacho documents): a compact second
    # rendition of the document appears *after* the boilerplate footer —
    # different wording, must be preserved verbatim, never mistaken for
    # more boilerplate.
    body = (
        "<p>Texto integral do despacho.</p>"
        + SIGNATURE_BLOCK
        + "<p>DESPACHO N&ordm; 2785 - ementa compacta e distinta do texto acima.</p>"
    )
    source = _write_html(tmp_path, body)
    out_path = tmp_path / "out.md"

    result = HtmlSeiRoute().extract(source, out_path)
    assert result.status == "extracted"
    markdown = out_path.read_text(encoding="utf-8")
    assert "Texto integral do despacho." in markdown
    assert "ementa compacta e distinta do texto acima." in markdown


def test_keeps_a_partys_own_quoted_use_of_the_signature_phrase(tmp_path: Path):
    # Mirrors a real file in the corpus (Ofício 1390,
    # 48500.023369/2026-23): the phrase "assinado eletronicamente" appears
    # twice — once as SEI's own final stamp (removed, via the structural
    # <div unselectable="on"> rule) and once inside a party's quoted
    # statement about a *different*, unrelated electronic signature
    # ("a MQA reconhece ter assinado eletronicamente com a Copel..."). Only
    # the first is boilerplate; the second is case content and must survive
    # verbatim — proof that removal is scoped to the structural block, never
    # to the phrase's wording.
    body = (
        "<p>Em breve resumo, a MQA reconhece ter assinado eletronicamente "
        "com a Copel Comercialização S.A. uma Proposta Comercial "
        "em março de 2026.</p>" + SIGNATURE_BLOCK
    )
    source = _write_html(tmp_path, body)
    out_path = tmp_path / "out.md"

    result = HtmlSeiRoute().extract(source, out_path)
    assert result.status == "extracted"
    markdown = out_path.read_text(encoding="utf-8")
    assert "a MQA reconhece ter assinado eletronicamente com a Copel" in markdown
    # ...but the real SEI stamp (this fixture's own signer) is gone.
    assert "fulano de tal" not in markdown.lower()
    assert "código crc" not in markdown.lower()


def test_extracts_content_with_no_wrapping_p_tag_inside_a_div(tmp_path: Path):
    # Regression: the real "E-mail" tipo_documento has its content directly
    # inside <div id="conteudo"> with no <p> at all — just bare text, <br>
    # and inline tags like <b>. A walker that only recurses looking for
    # <p>/<div>/<table>/<h*> inside a <div> would silently drop this whole
    # document (found while validating this route against the real corpus
    # — every one of the 14 real "E-mail" documents hit this exact shape).
    body = (
        '<div id="titulo"><label>E-mail - 0341027</label></div>'
        '<div id="conteudo">'
        "<br /><b>Data de Envio</b>: <br />&nbsp;&nbsp;29/04/2026 11:37:20<br />"
        "<br /><b>Assunto</b>: <br />&nbsp;&nbsp;Restrição de documento<br />"
        "</div>"
    )
    source = _write_html(tmp_path, body)
    out_path = tmp_path / "out.md"

    result = HtmlSeiRoute().extract(source, out_path)

    assert result.status == "extracted"
    markdown = out_path.read_text(encoding="utf-8")
    assert "E-mail - 0341027" in markdown
    assert "Data de Envio" in markdown
    assert "29/04/2026 11:37:20" in markdown
    assert "Restrição de documento" in markdown


def test_reports_error_when_source_cannot_be_read(tmp_path: Path):
    missing = tmp_path / "does-not-exist.html"
    result = HtmlSeiRoute().extract(missing, tmp_path / "out.md")
    assert result.status == "error"
    assert result.message
