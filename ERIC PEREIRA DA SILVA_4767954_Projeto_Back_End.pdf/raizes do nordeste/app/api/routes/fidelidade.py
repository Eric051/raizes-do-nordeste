"""
Rotas do programa de fidelidade.

Endpoints (cliente ve so o proprio saldo/historico):
- GET /fidelidade/saldo
- GET /fidelidade/historico
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_usuario_atual
from app.api.schemas.comuns import PageMeta
from app.api.schemas.fidelidade import (
    HistoricoListResponse,
    MovimentacaoPontosResponse,
    SaldoResponse,
)
from app.application.services import fidelidade_service
from app.domain.entities.enums import PerfilUsuario
from app.domain.exceptions import SemPermissao
from app.infrastructure.database import models
from app.infrastructure.database.connection import get_db


router = APIRouter(prefix="/fidelidade", tags=["Fidelidade"])


@router.get(
    "/saldo",
    response_model=SaldoResponse,
    summary="Consulta o saldo de pontos do cliente logado",
)
def saldo(
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual),
):
    if usuario.perfil != PerfilUsuario.CLIENTE:
        raise SemPermissao(
            "Apenas usuarios com perfil CLIENTE possuem saldo de fidelidade."
        )
    saldo_atual = fidelidade_service.consultar_saldo(db, usuario.id)
    return SaldoResponse(
        cliente_id=usuario.id,
        saldo=saldo_atual,
        consentimento_ativo=usuario.consentimento_lgpd,
    )


@router.get(
    "/historico",
    response_model=HistoricoListResponse,
    summary="Lista o historico de movimentacoes de pontos",
)
def historico(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual),
):
    if usuario.perfil != PerfilUsuario.CLIENTE:
        raise SemPermissao(
            "Apenas usuarios com perfil CLIENTE possuem historico de fidelidade."
        )
    items, total = fidelidade_service.listar_historico(
        db, usuario.id, page=page, limit=limit
    )
    return HistoricoListResponse(
        items=[MovimentacaoPontosResponse.model_validate(m) for m in items],
        meta=PageMeta.calcular(page, limit, total),
    )
