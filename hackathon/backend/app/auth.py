"""Autenticacao por ``AUTH_MODE`` (issue #104, parent #101).

Decisao do contrato frontend <-> backend (secao ``AUTH_MODE``,
requirements/contracts/frontend-backend.md) e de topic-cognito-auth (#91):

- ``AUTH_MODE=none`` (padrao, Compose local): nenhuma rota exige header;
  ``get_identity`` devolve ``None`` e nada muda.
- ``AUTH_MODE=cognito`` (AWS): todo ``/v1/*`` exceto ``/v1/health`` exige
  ``Authorization: Bearer <access token>`` do User Pool, validado por
  assinatura (JWKS), ``iss``, ``client_id``, ``token_use=access`` e
  ``exp`` -> ``401`` se faltar ou falhar. O ``user_id`` e o claim
  ``username``; os grupos vem de ``cognito:groups``.
  ``/v1/users/{user_id}/*`` responde ``403`` se o caminho divergir do
  token; ``require_admin`` (``/v1/ingestions``, ``/v1/demo/reset``) exige
  o grupo ``admin``.

A identidade resolvida e gravada em ``request.state.user_id`` para o log
por requisicao (app/request_log.py).

Interface pequena: ``get_identity`` (dependencia FastAPI que entrega
``Identity``), ``require_admin`` e ``get_token_verifier``, que testes
substituem por ``dependency_overrides`` (ex.: ``CognitoTokenVerifier``
com a chave publica de um par RSA gerado no teste, sem rede).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request

from app.config import Settings

ADMIN_GROUP = "admin"


@dataclass(frozen=True)
class Identity:
    user_id: str
    groups: frozenset[str]


class InvalidTokenError(Exception):
    pass


class CognitoTokenVerifier:
    """Valida um access token do User Pool e devolve a ``Identity``.

    ``signing_key`` resolve o ``kid`` do header do token para a chave
    publica; em producao vem do JWKS do pool (``PyJWKClient``, buscado na
    primeira requisicao e mantido em cache).
    """

    def __init__(self, *, issuer: str, client_id: str, signing_key: Callable[[str], Any]):
        self._issuer = issuer
        self._client_id = client_id
        self._signing_key = signing_key

    def verify(self, token: str) -> Identity:
        try:
            kid = jwt.get_unverified_header(token).get("kid")
            if not kid:
                raise InvalidTokenError("token sem kid")
            claims = jwt.decode(
                token,
                self._signing_key(kid),
                algorithms=["RS256"],
                issuer=self._issuer,
                options={"require": ["exp", "iss", "token_use", "client_id", "username"]},
            )
        except (jwt.PyJWTError, KeyError, LookupError) as exc:
            raise InvalidTokenError(str(exc)) from exc
        if claims["token_use"] != "access":
            raise InvalidTokenError("token_use diferente de access")
        if claims["client_id"] != self._client_id:
            raise InvalidTokenError("client_id diferente do configurado")
        return Identity(
            user_id=claims["username"],
            groups=frozenset(claims.get("cognito:groups") or []),
        )


def build_cognito_verifier(settings: Settings) -> CognitoTokenVerifier:
    issuer = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}"
    )
    jwks = jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_keys=True, lifespan=86400)
    return CognitoTokenVerifier(
        issuer=issuer,
        client_id=settings.cognito_client_id,
        signing_key=lambda kid: jwks.get_signing_key(kid).key,
    )


def validate_auth_settings(settings: Settings) -> None:
    """Falha cedo (no ``create_app``) se o modo de auth estiver incompleto."""
    if settings.auth_mode == "none":
        return
    if settings.auth_mode != "cognito":
        raise RuntimeError(f"AUTH_MODE={settings.auth_mode!r} invalido: use 'none' ou 'cognito'.")
    missing = [
        name
        for name, value in (
            ("COGNITO_REGION", settings.cognito_region),
            ("COGNITO_USER_POOL_ID", settings.cognito_user_pool_id),
            ("COGNITO_CLIENT_ID", settings.cognito_client_id),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("AUTH_MODE=cognito exige " + ", ".join(missing) + " configurado(s).")


def get_token_verifier(request: Request) -> CognitoTokenVerifier | None:
    return request.app.state.token_verifier


def get_identity(
    request: Request,
    verifier: CognitoTokenVerifier | None = Depends(get_token_verifier),
) -> Identity | None:
    if request.app.state.auth_mode == "none":
        return None

    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token or verifier is None:
        raise _unauthorized()
    try:
        identity = verifier.verify(token.strip())
    except InvalidTokenError as exc:
        raise _unauthorized() from exc

    request.state.user_id = identity.user_id
    path_user_id = request.path_params.get("user_id")
    if path_user_id is not None and path_user_id != identity.user_id:
        raise HTTPException(status_code=403, detail="user_id do caminho difere do token")
    return identity


def require_admin(identity: Identity | None = Depends(get_identity)) -> None:
    if identity is not None and ADMIN_GROUP not in identity.groups:
        raise HTTPException(status_code=403, detail="Requer o grupo admin")


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Token ausente, expirado ou invalido",
        headers={"WWW-Authenticate": "Bearer"},
    )
