"""
Rota /auditoria - somente leitura, restrita a ADMIN.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_perfis
from app.api.schemas.auditoria import (
    LogAuditoriaListResponse,
    LogAuditoriaResponse,
)
from app.api.schemas.comuns import PageMeta
from app.application.services import auditoria_service
from app.domain.entities.enums import PerfilUsuario
from app.infrastructure.database.connection import get_db


router = APIRouter(prefix="/auditoria", tags=["Auditoria"])


@router.get(
    "",
    response_model=LogAuditoriaListResponse,
    summary="Lista os logs de auditoria (somente ADMIN)",
    description=(
        "Permite ao ADMIN auditar acoes sensiveis do sistema. "
        "Aceita filtros por usuario, acao, recurso e periodo."
    ),
    dependencies=[Depends(exigir_perfis(PerfilUsuario.ADMIN))],
)
def listar(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    usuario_id: Optional[int] = Query(None, description="Filtra pelo usuario que executou a acao"),
    acao: Optional[str] = Query(None, description="Codigo da acao (ex: PEDIDO_CRIADO)"),
    recurso: Optional[str] = Query(None, description="Tipo do recurso (ex: PEDIDO)"),
    desde: Optional[datetime] = Query(None, description="Inicio do periodo (ISO 8601)"),
    ate: Optional[datetime] = Query(None, description="Fim do periodo (ISO 8601)"),
    db: Session = Depends(get_db),
):
    items, total = auditoria_service.listar_logs(
        db,
        page=page,
        limit=limit,
        usuario_id=usuario_id,
        acao=acao,
        recurso=recurso,
        desde=desde,
        ate=ate,
    )
    return LogAuditoriaListResponse(
        items=[LogAuditoriaResponse.model_validate(log) for log in items],
        meta=PageMeta.calcular(page, limit, total),
    )
