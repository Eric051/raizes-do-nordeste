"""
Rotas do recurso Estoque (sub-recurso de /unidades).

URLs:
- GET  /unidades/{unidade_id}/estoque
- POST /unidades/{unidade_id}/estoque/movimentacoes
- GET  /unidades/{unidade_id}/estoque/movimentacoes

Permissoes:
- GET sao acessiveis a qualquer usuario autenticado.
- POST de movimentacao eh restrito a ADMIN e GERENTE
  (saidas por venda acontecem automaticamente quando o pedido eh
  pago, sem precisar de chamada manual).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_perfis, get_usuario_atual
from app.api.schemas.comuns import PageMeta
from app.api.schemas.estoque import (
    MovimentacaoEstoqueCreate,
    MovimentacaoEstoqueResponse,
    MovimentacaoListResponse,
    SaldoEstoqueResponse,
    SaldoListResponse,
)
from app.application.services import estoque_service
from app.domain.entities.enums import PerfilUsuario
from app.infrastructure.database import models
from app.infrastructure.database.connection import get_db


router = APIRouter(prefix="/unidades/{unidade_id}/estoque", tags=["Estoque"])

PERFIS_GESTAO = [PerfilUsuario.ADMIN, PerfilUsuario.GERENTE]


@router.get(
    "",
    response_model=SaldoListResponse,
    summary="Lista os saldos de estoque de uma unidade",
    dependencies=[Depends(get_usuario_atual)],
)
def listar_saldos(
    unidade_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = estoque_service.listar_saldos_da_unidade(
        db, unidade_id, page=page, limit=limit
    )
    return SaldoListResponse(items=items, meta=PageMeta.calcular(page, limit, total))


@router.post(
    "/movimentacoes",
    response_model=SaldoEstoqueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra uma movimentacao de estoque (entrada, saida ou ajuste)",
)
def criar_movimentacao(
    unidade_id: int,
    dados: MovimentacaoEstoqueCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(exigir_perfis(*PERFIS_GESTAO)),
):
    estoque = estoque_service.criar_movimentacao(
        db, unidade_id=unidade_id, dados=dados, responsavel_id=usuario.id
    )
    # busca o nome do produto pra resposta
    produto = db.query(models.Produto).filter_by(id=estoque.produto_id).first()
    return SaldoEstoqueResponse(
        unidade_id=estoque.unidade_id,
        produto_id=estoque.produto_id,
        nome_produto=produto.nome if produto else "",
        quantidade=estoque.quantidade,
        atualizado_em=estoque.atualizado_em,
    )


@router.get(
    "/movimentacoes",
    response_model=MovimentacaoListResponse,
    summary="Lista o historico de movimentacoes de estoque da unidade",
    dependencies=[Depends(get_usuario_atual)],
)
def listar_historico(
    unidade_id: int,
    produto_id: Optional[int] = Query(None, description="Filtra por produto"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = estoque_service.listar_movimentacoes(
        db, unidade_id=unidade_id, produto_id=produto_id, page=page, limit=limit
    )
    return MovimentacaoListResponse(
        items=[MovimentacaoEstoqueResponse.model_validate(m) for m in items],
        meta=PageMeta.calcular(page, limit, total),
    )
