"""
Schemas Pydantic do programa de fidelidade.

A regra do programa eh simples e fica em app/domain/regras/pedido.py:
- 1 ponto a cada R$ 1,00 (arredondado pra baixo) creditado quando o
  pedido vai pra status PAGO
- 1 ponto = R$ 0,10 de desconto no proximo pedido (resgate)

A LGPD exige consentimento explicito pra usar fidelidade, ja que ela
trata o perfil de consumo do cliente. Sem consentimento ativo, o
sistema nao credita nem permite resgatar.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.comuns import PageMeta
from app.domain.entities.enums import TipoMovimentacaoPontos


class SaldoResponse(BaseModel):
    """Saldo atual de pontos do cliente."""
    cliente_id: int
    saldo: int = Field(..., ge=0)
    consentimento_ativo: bool = Field(
        ...,
        description=(
            "Indica se o cliente tem consentimento LGPD ativo. Sem "
            "consentimento, o programa nao credita nem deixa resgatar."
        ),
    )


class MovimentacaoPontosResponse(BaseModel):
    """Item do historico de movimentacoes de pontos."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: TipoMovimentacaoPontos
    pontos: int
    descricao: Optional[str] = None
    pedido_id: Optional[int] = None
    criado_em: datetime


class HistoricoListResponse(BaseModel):
    items: list[MovimentacaoPontosResponse]
    meta: PageMeta
