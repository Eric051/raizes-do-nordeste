"""
Handlers globais de excecao.

A ideia eh deixar todos os erros da API saindo no MESMO formato JSON,
independente de quem os levantou (DominioError dos services,
HTTPException do FastAPI, RequestValidationError do Pydantic, etc).

Isso facilita o consumo da API por outros sistemas e bate com o
requisito do roteiro de "padrao de erro consistente".
"""
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions import DominioError


def _resposta(
    error_code: str,
    message: str,
    status_code: int,
    path: str,
    details: list | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_code,
            "message": message,
            "details": details or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": path,
        },
    )


async def dominio_error_handler(request: Request, exc: DominioError):
    """Captura excecoes de dominio levantadas pelos services."""
    return _resposta(
        exc.error_code,
        exc.message,
        exc.http_status,
        str(request.url.path),
        exc.details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Padroniza HTTPException levantada pelo proprio FastAPI."""
    mapa = {
        401: "NAO_AUTENTICADO",
        403: "SEM_PERMISSAO",
        404: "RECURSO_NAO_ENCONTRADO",
        405: "METODO_NAO_PERMITIDO",
        409: "CONFLITO",
    }
    error_code = mapa.get(exc.status_code, "ERRO_HTTP")
    mensagem = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _resposta(error_code, mensagem, exc.status_code, str(request.url.path))


async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Padroniza erros de validacao do Pydantic."""
    details = []
    for err in exc.errors():
        # err["loc"] vem tipo ('body', 'email'). Tirando o primeiro item
        # pra deixar so o caminho do campo no payload.
        loc = err.get("loc", [])
        campo = ".".join(str(l) for l in loc[1:]) if len(loc) > 1 else None
        details.append({"field": campo, "issue": err.get("msg", "valor invalido")})

    return _resposta(
        "DADOS_INVALIDOS",
        "Dados de entrada invalidos.",
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        str(request.url.path),
        details,
    )


def registrar_handlers(app: FastAPI) -> None:
    """Registra todos os handlers no app FastAPI."""
    app.add_exception_handler(DominioError, dominio_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
