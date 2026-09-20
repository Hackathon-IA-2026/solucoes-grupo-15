"""Port ``Mailer`` + adapter de previa (TB1 Ticket 8, issue #24).

A conta do hackathon nao tem SES (ver i9-integration.md, issue-7); o
que se especifica e a entrega de notificacao por e-mail atras de um
port `Mailer`, independente do adapter - so um adapter existe nesta
fase: ``PreviewMailer``. Frequencia e deduplicacao sao politica do
`backend`, aplicadas *antes* de chamar `Mailer.send` (ver
app/notifications.py::run_notifications) - o adapter recebe a mensagem
ja pronta e so precisa ser idempotente por ``email_id``.

"Enviar" nesta fase demo significa gravar uma linha em ``email_digest``
- e isso que "grava/expoe o conteudo renderizado na pagina inicial"
significa (GET /v1/users/{user_id}/email-digests, ver
app/routes/notifications.py). Nenhuma chamada de rede/SES acontece
aqui.
"""

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import EmailDigest


@dataclass(frozen=True)
class DeliveryReport:
    """Espelha o resultado de ``Mailer.send`` (i9-integration.md).

    ``status`` e sempre ``"previewed"`` neste adapter (nunca
    ``"sent"``/entrega real) - a distincao entre previa gerada e e-mail
    de verdade enviado precisa ficar visivel na interface e nos
    eventos de telemetria (i6-telemetry.md).
    """

    email_id: str
    adapter: str
    status: str


class PreviewMailer:
    """Adapter de previa do port ``Mailer``.

    Idempotente por ``email_id``: se ja existe um ``email_digest`` com
    esse id, nao duplica a linha (no-op) e devolve o mesmo relatorio -
    cobre o caso de ``send`` ser chamado duas vezes para o mesmo
    digest (ver TDD seam 3 da issue #24).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def send(
        self,
        email_id: str,
        to: str,
        subject: str,
        body: str,
        *,
        user_id: str,
        ingestion_job_id: str,
        notification_ids: list[int],
    ) -> DeliveryReport:
        del to, subject  # a previa nao envia de verdade; guardados so por contrato.
        existing = self._session.get(EmailDigest, email_id)
        if existing is None:
            self._session.add(
                EmailDigest(
                    email_id=email_id,
                    user_id=user_id,
                    ingestion_job_id=ingestion_job_id,
                    notification_ids_json=json.dumps(notification_ids),
                    rendered_body=body,
                )
            )
            self._session.flush()

        return DeliveryReport(email_id=email_id, adapter="preview", status="previewed")
