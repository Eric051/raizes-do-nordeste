"""
Gateway de pagamento simulado.

Simula uma chamada HTTP externa: pode levar alguns ms (sleep), pode
falhar por "rede" (10% das vezes) e devolve um resultado APROVADO ou
RECUSADO. Tem um parametro pra forcar o resultado, util pros testes
do Postman.

DECISAO IMPORTANTE: o mock NAO recebe dados de cartao. So valor,
metodo e identificador interno do pedido. Isso bate com a politica
da Raizes do Nordeste descrita no estudo de caso ("a empresa nao
processa pagamentos diretamente em seu sistema principal") e com
boas praticas de LGPD/PCI: dados sensiveis nunca passam por aqui.
"""
import random
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.config import settings
from app.domain.entities.enums import StatusPagamento


# 10% de chance de simular erro transient (timeout / rede caindo).
# Permite mostrar tolerancia a falhas no fluxo critico.
PROBABILIDADE_FALHA_TRANSIENT = 0.10

# latencia simulada da chamada externa (segundos)
LATENCIA_SEGUNDOS = 0.05


class FalhaTransientGateway(Exception):
    """
    Falha temporaria de comunicacao com o gateway. O service pode
    fazer retry. Diferente de FalhaIntegracaoExterna que eh um erro
    final pra cima.
    """
    pass


@dataclass
class RespostaGateway:
    aprovado: bool
    status: StatusPagamento
    referencia_externa: str
    mensagem: str
    payload_bruto: dict


def processar_pagamento(
    valor: Decimal,
    metodo: str,
    pedido_id: int,
    forcar_resultado: Optional[str] = None,
) -> RespostaGateway:
    """
    Simula a chamada externa de processamento de pagamento.

    Parametros:
        valor: total a ser cobrado
        metodo: forma de pagamento informada (so pra log)
        pedido_id: id interno do pedido (so pra log)
        forcar_resultado:
            - "APROVADO" / "RECUSADO" / "ERRO": forca o resultado (testes)
            - None: usa PAYMENT_MOCK_DEFAULT_OUTCOME do .env
                    ("APROVADO", "RECUSADO" ou "ALEATORIO")

    Levanta FalhaTransientGateway aleatoriamente (~10% das chamadas
    nao forcadas) pra simular falhas de rede.
    """
    time.sleep(LATENCIA_SEGUNDOS)

    # ERRO forcado vira excecao transient sem rodar nada
    if forcar_resultado and forcar_resultado.upper() == "ERRO":
        raise FalhaTransientGateway("erro forcado pelo cliente do gateway")

    # falha aleatoria so quando o teste nao forcou um resultado
    if forcar_resultado is None and random.random() < PROBABILIDADE_FALHA_TRANSIENT:
        raise FalhaTransientGateway("timeout simulado na comunicacao com o gateway")

    resultado = (forcar_resultado or settings.payment_mock_default_outcome).upper()
    if resultado == "ALEATORIO":
        resultado = random.choice(["APROVADO", "RECUSADO"])

    referencia = f"MOCK-{uuid.uuid4().hex[:12].upper()}"

    if resultado == "APROVADO":
        return RespostaGateway(
            aprovado=True,
            status=StatusPagamento.APROVADO,
            referencia_externa=referencia,
            mensagem="Pagamento aprovado",
            payload_bruto={
                "transacao_id": referencia,
                "status": "approved",
                "valor": str(valor),
                "metodo": metodo,
                "pedido_id": pedido_id,
            },
        )

    # qualquer outra coisa eh tratada como recusa
    return RespostaGateway(
        aprovado=False,
        status=StatusPagamento.RECUSADO,
        referencia_externa=referencia,
        mensagem="Pagamento recusado pelo emissor",
        payload_bruto={
            "transacao_id": referencia,
            "status": "denied",
            "valor": str(valor),
            "metodo": metodo,
            "pedido_id": pedido_id,
            "motivo": "saldo_insuficiente",
        },
    )
