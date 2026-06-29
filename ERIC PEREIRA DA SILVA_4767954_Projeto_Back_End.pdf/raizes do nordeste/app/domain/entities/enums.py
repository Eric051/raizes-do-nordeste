"""
Enumeracoes do dominio.

Mantenho todas aqui pra facilitar achar e evitar duplicacao entre as
entidades. Como sao "str, Enum" eh facil serializar pra JSON e validar
nos schemas Pydantic.
"""
from enum import Enum


class PerfilUsuario(str, Enum):
    """Perfis de acesso do sistema. Cada um tem permissoes diferentes."""
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    ATENDENTE = "ATENDENTE"
    COZINHA = "COZINHA"
    CLIENTE = "CLIENTE"


class CanalPedido(str, Enum):
    """
    Canal de origem do pedido. Campo OBRIGATORIO em todo pedido,
    conforme requisito de multicanalidade do roteiro.
    """
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"
    WEB = "WEB"


class StatusPedido(str, Enum):
    """
    Estados pelos quais um pedido passa ao longo do tempo.

    Fluxo principal:
        AGUARDANDO_PAGAMENTO -> PAGO -> EM_PREPARO -> PRONTO -> ENTREGUE

    Caminhos alternativos:
        AGUARDANDO_PAGAMENTO -> PAGAMENTO_RECUSADO (cliente pode tentar
        de novo ou cancelar);
        Qualquer estado anterior a PRONTO -> CANCELADO.
    """
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGAMENTO_RECUSADO = "PAGAMENTO_RECUSADO"
    PAGO = "PAGO"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


class StatusPagamento(str, Enum):
    """Status de uma tentativa individual de pagamento."""
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"
    ERRO = "ERRO"


class MetodoPagamento(str, Enum):
    """Forma de pagamento escolhida no pedido."""
    PIX = "PIX"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    DINHEIRO = "DINHEIRO"
    MOCK = "MOCK"  # usado nos testes pra forcar comportamento


class TipoMovimentacaoEstoque(str, Enum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"
    AJUSTE = "AJUSTE"


class TipoMovimentacaoPontos(str, Enum):
    CREDITO = "CREDITO"
    RESGATE = "RESGATE"
    EXPIRADO = "EXPIRADO"
    AJUSTE = "AJUSTE"


class CategoriaProduto(str, Enum):
    """Categorias do cardapio. Usado pra filtros e relatorios."""
    TAPIOCA = "TAPIOCA"
    CUSCUZ = "CUSCUZ"
    BOLO = "BOLO"
    BEBIDA = "BEBIDA"
    CAFE_DA_MANHA = "CAFE_DA_MANHA"
    SALGADO = "SALGADO"
    OUTRO = "OUTRO"
