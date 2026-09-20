"""Configuracao do backend via variaveis de ambiente.

Valores padrao seguem a decisao i2-model-serving (local, sem
credenciais AWS por padrao): EMBEDDER=fake e MAILER=preview. Nenhuma
variavel de credencial AWS e lida aqui - troca de adapter real
(Bedrock/SES) fica para tickets futuros.

``default_corpus_version`` (Ticket 3, issue #19) e o fallback do
envelope de POST /v1/search quando ``results`` fica vazio (nenhum hit
devolvido pelo ai, logo nenhuma familia da qual derivar o
``corpus_version`` do catalogo) - hoje coincide com o
``corpus_version`` do corpus fixture (app/fixtures/demo_corpus.json,
"demo-v1"), mas fica configuravel por variavel de ambiente para nao
prender o codigo a esse valor.

``code_reference`` (Ticket 9, issue #25) e a referencia de
commit/ambiente gravada junto de cada ``search_execution`` (ver
app/routes/search.py), para reprodutibilidade auditavel
(i7-reproducibility). Le a variavel de ambiente ``CODE_REFERENCE`` se
presente; caso contrario tenta ler o commit atual de
``.git/HEAD``/``.git/refs/...`` na raiz do repo (sem exigir o binario
`git` instalado). Qualquer falha (repo nao encontrado, ref
empacotada/detached de forma inesperada, etc.) cai para a string
``"unknown"`` - isto e so uma referencia auditavel, nao precisa ser
sofisticado.
"""

import os
import pathlib
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    ai_base_url: str
    embedder: str
    mailer: str
    database_url: str
    default_corpus_version: str
    code_reference: str


def _read_git_code_reference() -> str:
    try:
        # app/config.py -> app -> backend -> hackathon -> raiz do repo.
        repo_root = pathlib.Path(__file__).resolve().parents[3]
        git_dir = repo_root / ".git"
        head_content = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if head_content.startswith("ref:"):
            ref_relative = head_content.split(" ", 1)[1].strip()
            return (git_dir / ref_relative).read_text(encoding="utf-8").strip()
        return head_content
    except Exception:
        return "unknown"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        ai_base_url=os.environ.get("AI_BASE_URL", "http://ai:8000"),
        embedder=os.environ.get("EMBEDDER", "fake"),
        mailer=os.environ.get("MAILER", "preview"),
        database_url=os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://capiwatt:capiwatt@postgres:5432/capiwatt",
        ),
        default_corpus_version=os.environ.get("DEFAULT_CORPUS_VERSION", "demo-v1"),
        code_reference=os.environ.get("CODE_REFERENCE") or _read_git_code_reference(),
    )
