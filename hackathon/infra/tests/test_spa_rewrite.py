"""Logica da CloudFront Function de fallback de SPA (issue #107).

Executa ``spa_rewrite.js`` no node com eventos no formato do viewer-request
do CloudFront. Os ids de processo SEI tem ponto (``48500.001234/2024-11``,
codificado como ``48500.001234%2F2024-11``), entao "tem ponto" nao pode
bastar para tratar o caminho como arquivo.
"""

import json
import shutil
import subprocess

import pytest

from capiwatt_infra.frontend import SPA_REWRITE_JS

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node indisponivel")


def _rewrite(uris: list[str]) -> list[str]:
    script = (
        SPA_REWRITE_JS.read_text()
        + "\nconst uris = JSON.parse(process.argv[1]);"
        + "\nconsole.log(JSON.stringify(uris.map((uri) =>"
        + " handler({ request: { method: 'GET', uri, querystring: {}, headers: {} } }).uri)));"
    )
    out = subprocess.run(
        ["node", "-e", script, json.dumps(uris)], check=True, capture_output=True, text=True
    )
    return json.loads(out.stdout)


def test_app_routes_and_deep_links_are_served_by_index_html():
    routes = [
        "/",
        "/login",
        "/explorar",
        "/integracoes/notificacoes",
        "/documents/fam-norma-1000",
        "/processos/48500.001234%2F2024-11",
        "/processos/48500.001234",
        "/documents/",
    ]
    assert _rewrite(routes) == ["/index.html"] * len(routes)


def test_static_files_keep_their_path():
    files = [
        "/index.html",
        "/config.json",
        "/favicon.svg",
        "/apple-touch-icon.png",
        "/assets/index-x2ywK11e.js",
        "/assets/index-BMa7KH1O.css",
        "/assets/capiwatt-mascote.jpg",
        "/assets/nao-existe.js",
    ]
    assert _rewrite(files) == files
