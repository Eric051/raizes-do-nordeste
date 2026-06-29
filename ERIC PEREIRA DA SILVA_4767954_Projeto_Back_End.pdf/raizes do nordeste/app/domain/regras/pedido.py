"""
Regras puras do dominio Pedido.

Coloquei aqui tudo o que eh decisao de negocio e nao depende de banco
nem de framework web: transicao de status, calculo de total, regras
de cancelamento, calculo de pontos da fidelidade, etc.

Como sao funcoes puras, da pra testar facil sem precisar levantar
o sistema todo.
"""
from decimal import Decimal

from app.domain.entities.enums import StatusPedido
from app.domain.exceptions import TransicaoInvalida


# Mapa de transicoes permitidas. A chave eh o estado atual e o valor
# eh o conjunto de estados pra onde aquele estado pode ir.
TRANSICOES_PERMITIDAS: dict[StatusPedido, set[StatusPedido]] = {
    StatusPedido.AGUARDANDO_PAGAMENTO: {
        StatusPedido.PAGO,
        StatusPedido.PAGAMENTO_RECUSADO,
        StatusPedido.CANCELADO,
    },
    StatusPedido.PAGAMENTO_RECUSADO: {
        StatusPedido.AGUARDANDO_PAGAMENTO,  # cliente tentou de novo
        StatusPedido.CANCELADO,
    },
    StatusPedido.PAGO: {
        StatusPedido.EM_PREPARO,
        StatusPedido.CANCELADO,  # cancelamento com estorno
    },
    StatusPedido.EM_PREPARO: {
        StatusPedido.PRONTO,
        StatusPedido.CANCELADO,
    },
    StatusPedido.PRONTO: {
        StatusPedido.ENTREGUE,
    },
    StatusPedido.ENTREGUE: set(),  # estado final
    StatusPedido.CANCELADO: set(),  # estado final
}


def validar_transicao(atual: StatusPedido, novo: StatusPedido) -> None:
    """
    Verifica se a transicao de status eh permitida.
    Levanta TransicaoInvalida se nao for.
    """
    if novo == atual:
        raise TransicaoInvalida(
            f"O pedido ja esta no status {atual.value}.",
            details=[{"field": "status", "issue": "estado igual ao atual"}],
        )

    permitidos = TRANSICOES_PERMITIDAS.get(atual, set())
    if novo not in permitidos:
        permitidos_str = ", ".join(sorted(p.value for p in permitidos)) or "(nenhum)"
        raise TransicaoInvalida(
            f"Nao eh possivel mudar de {atual.value} para {novo.value}.",
            details=[{"field": "status", "issue": f"transicoes permitidas: {permitidos_str}"}],
        )


def calcular_subtotal(itens: list[tuple[Decimal, int]]) -> Decimal:
    """
    Recebe uma lista de tuplas (preco_unitario, quantidade) e devolve
    o subtotal. Mantenho como funcao pura pra poder testar isolada.
    """
    total = Decimal("0.00")
    for preco, qtd in itens:
        if qtd <= 0:
            continue
        total += Decimal(preco) * qtd
    return total.quantize(Decimal("0.01"))


def aplicar_desconto(
    subtotal: Decimal,
    percentual: Decimal | None = None,
    valor_fixo: Decimal | None = None,
) -> Decimal:
    """
    Calcula o valor de desconto a aplicar sobre o subtotal.

    Aceita percentual (0 a 100) ou valor fixo. Se ambos vierem, soma
    os dois (cenario raro, mas o codigo aceita). Garante que o desconto
    nao ultrapasse o proprio subtotal.
    """
    desconto = Decimal("0.00")
    if percentual is not None and percentual > 0:
        desconto += subtotal * (Decimal(percentual) / Decimal("100"))
    if valor_fixo is not None and valor_fixo > 0:
        desconto += Decimal(valor_fixo)

    desconto = min(desconto, subtotal)
    return desconto.quantize(Decimal("0.01"))


# Regra do programa de fidelidade:
# - 1 ponto a cada R$ 1,00 gasto (arredondado pra baixo)
# - 100 pontos resgatam R$ 10,00 de desconto (1 ponto = R$ 0,10)
PONTOS_POR_REAL = Decimal("1")
VALOR_POR_PONTO = Decimal("0.10")


def calcular_pontos_a_creditar(total: Decimal) -> int:
    """
    Quantos pontos um cliente recebe ao pagar um pedido com aquele total.
    Arredonda pra baixo: R$ 49,90 vira 49 pontos.
    """
    if total <= 0:
        return 0
    return int((total * PONTOS_POR_REAL).to_integral_value(rounding="ROUND_DOWN"))


def calcular_desconto_resgate(pontos: int) -> Decimal:
    """Quanto vale, em reais, resgatar X pontos."""
    if pontos <= 0:
        return Decimal("0.00")
    return (Decimal(pontos) * VALOR_POR_PONTO).quantize(Decimal("0.01"))
