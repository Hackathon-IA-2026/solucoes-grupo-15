"""Helpers de catalogo compartilhados entre rotas publicas.

Extrai a regra de "face" de uma familia (a versao de maior
``version_date`` - comparacao de string funciona porque o formato e
ISO AAAA-MM-DD e ordena lexicograficamente) para um unico lugar,
reusado por POST /v1/search (app/routes/search.py) e por
GET /v1/documents/{family_id} (app/routes/documents.py, Ticket 4,
issue #20). Nenhuma regra nova: e exatamente a logica que ja existia
em app/routes/search.py desde o Ticket 3 (issue #19).
"""

from app.models import DocumentVersion


def select_face_version(versions: list[DocumentVersion]) -> DocumentVersion:
    """Devolve a versao de maior ``version_date`` dentre ``versions``.

    ``versions`` nunca deve ser vazia - quem chama e responsavel por
    garantir isso (ex.: checar a familia existe antes).
    """
    return max(versions, key=lambda v: v.version_date)
