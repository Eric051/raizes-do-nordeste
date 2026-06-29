"""
Schemas Pydantic do recurso Auditoria.

Auditoria eh somente leitura via API: a escrita acontece direto
pelos services do sistema, atraves do helper audit_logger.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.api.schemas.comuns import PageMeta


class LogAuditoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: Optional[int] = None
    acao: str
    recurso: Optional[str] = None
    recurso_id: Optional[str] = None
    dados: Optional[str] = None
    ip_origem: Optional[str] = None
    criado_em: datetime


class LogAuditoriaListResponse(BaseModel):
    items: list[LogAuditoriaResponse]
    meta: PageMeta
