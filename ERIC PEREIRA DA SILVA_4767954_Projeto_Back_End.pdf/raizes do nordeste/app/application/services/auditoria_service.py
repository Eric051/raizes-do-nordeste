"""
Casos de uso de consulta da auditoria.

A escrita eh feita pelo audit_logger (chamado direto pelos outros
services). Aqui ficam so as consultas que o endpoint /auditoria
expoe pro ADMIN.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.database import models


def listar_logs(
    db: Session,
    page: int = 1,
    limit: int = 50,
    usuario_id: Optional[int] = None,
    acao: Optional[str] = None,
    recurso: Optional[str] = None,
    desde: Optional[datetime] = None,
    ate: Optional[datetime] = None,
) -> tuple[list[models.LogAuditoria], int]:
    query = db.query(models.LogAuditoria)
    if usuario_id is not None:
        query = query.filter(models.LogAuditoria.usuario_id == usuario_id)
    if acao:
        query = query.filter(models.LogAuditoria.acao == acao.upper())
    if recurso:
        query = query.filter(models.LogAuditoria.recurso == recurso.upper())
    if desde:
        query = query.filter(models.LogAuditoria.criado_em >= desde)
    if ate:
        query = query.filter(models.LogAuditoria.criado_em <= ate)

    total = query.count()
    items = (
        query.order_by(models.LogAuditoria.criado_em.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total
