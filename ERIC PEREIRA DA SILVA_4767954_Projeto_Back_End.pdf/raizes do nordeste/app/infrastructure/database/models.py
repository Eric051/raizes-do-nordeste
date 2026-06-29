"""
Modelos SQLAlchemy do sistema Raizes do Nordeste.

Concentro todas as tabelas neste arquivo pra manter visiveis as
relacoes entre elas. Em projetos maiores eu separaria por modulo,
mas pro escopo academico esse arquivo unico fica mais facil de revisar.

Padrao adotado:
- nomes de tabela no plural e em snake_case
- chaves primarias chamadas "id"
- timestamps "criado_em" / "atualizado_em" usando server_default=func.now()
- ENUMs do dominio sao mapeados como SQLEnum
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.domain.entities.enums import (
    CanalPedido,
    CategoriaProduto,
    MetodoPagamento,
    PerfilUsuario,
    StatusPagamento,
    StatusPedido,
    TipoMovimentacaoEstoque,
    TipoMovimentacaoPontos,
)
from app.infrastructure.database.connection import Base


# ----------------------------------------------------------------------
# Usuarios e perfis
# ----------------------------------------------------------------------

class Usuario(Base):
    """
    Usuario do sistema. Pode ser cliente, atendente, cozinha,
    gerente ou admin. O perfil define as permissoes na API.
    """
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    cpf = Column(String(14), unique=True, nullable=True)
    perfil = Column(
        SQLEnum(PerfilUsuario, name="perfil_usuario_enum"),
        nullable=False,
        default=PerfilUsuario.CLIENTE,
    )
    consentimento_lgpd = Column(Boolean, nullable=False, default=False)
    data_consentimento = Column(DateTime, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=False)
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # relacionamentos (carregamento lazy por padrao)
    pedidos = relationship(
        "Pedido", back_populates="cliente", foreign_keys="Pedido.cliente_id"
    )
    pontos_fidelidade = relationship(
        "PontosFidelidade", back_populates="cliente", uselist=False
    )
    movimentacoes_pontos = relationship(
        "MovimentacaoPontos", back_populates="cliente"
    )
    movimentacoes_estoque = relationship(
        "MovimentacaoEstoque", back_populates="responsavel"
    )
    logs_auditoria = relationship("LogAuditoria", back_populates="usuario")


# ----------------------------------------------------------------------
# Unidades, produtos e cardapio
# ----------------------------------------------------------------------

class Unidade(Base):
    """Cada loja fisica da rede. Tem cardapio e estoque proprios."""
    __tablename__ = "unidades"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    cidade = Column(String(100), nullable=False)
    estado = Column(String(2), nullable=False)  # UF
    endereco = Column(String(255), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=False)

    # relacoes
    cardapio = relationship("CardapioUnidade", back_populates="unidade", cascade="all, delete-orphan")
    estoque = relationship("Estoque", back_populates="unidade", cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="unidade")


class Produto(Base):
    """
    Catalogo geral da rede. O preco aqui eh o "preco base"; cada
    unidade pode definir um preco proprio na tabela CardapioUnidade.
    """
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    descricao = Column(Text, nullable=True)
    preco_base = Column(Numeric(10, 2), nullable=False)
    categoria = Column(
        SQLEnum(CategoriaProduto, name="categoria_produto_enum"),
        nullable=False,
        default=CategoriaProduto.OUTRO,
    )
    sazonal = Column(Boolean, nullable=False, default=False)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=False)

    cardapios = relationship("CardapioUnidade", back_populates="produto")
    estoques = relationship("Estoque", back_populates="produto")
    itens_pedido = relationship("ItemPedido", back_populates="produto")

    __table_args__ = (
        CheckConstraint("preco_base >= 0", name="ck_produto_preco_nao_negativo"),
    )


class CardapioUnidade(Base):
    """
    Vincula um produto a uma unidade, indicando se esta disponivel
    e qual o preco local. Se preco_local for nulo, usa o preco_base
    do produto. Permite o cenario do estudo de caso onde algumas
    unidades nao tem certos produtos ou cobram diferente.
    """
    __tablename__ = "cardapio_unidade"

    id = Column(Integer, primary_key=True, index=True)
    unidade_id = Column(Integer, ForeignKey("unidades.id", ondelete="CASCADE"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False)
    preco_local = Column(Numeric(10, 2), nullable=True)
    disponivel = Column(Boolean, nullable=False, default=True)

    unidade = relationship("Unidade", back_populates="cardapio")
    produto = relationship("Produto", back_populates="cardapios")

    __table_args__ = (
        UniqueConstraint("unidade_id", "produto_id", name="uq_cardapio_unidade_produto"),
    )


# ----------------------------------------------------------------------
# Estoque
# ----------------------------------------------------------------------

class Estoque(Base):
    """
    Saldo atual de um produto em uma unidade. Uma linha por
    par (unidade, produto). As entradas e saidas detalhadas ficam
    em MovimentacaoEstoque.
    """
    __tablename__ = "estoques"

    id = Column(Integer, primary_key=True, index=True)
    unidade_id = Column(Integer, ForeignKey("unidades.id", ondelete="CASCADE"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False)
    quantidade = Column(Integer, nullable=False, default=0)
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    unidade = relationship("Unidade", back_populates="estoque")
    produto = relationship("Produto", back_populates="estoques")
    movimentacoes = relationship(
        "MovimentacaoEstoque", back_populates="estoque", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("unidade_id", "produto_id", name="uq_estoque_unidade_produto"),
        CheckConstraint("quantidade >= 0", name="ck_estoque_qtd_nao_negativa"),
    )


class MovimentacaoEstoque(Base):
    """
    Historico de cada entrada e saida no estoque. Permite auditoria
    e relatorios. Toda venda gera uma SAIDA, toda reposicao gera
    uma ENTRADA, e ajustes manuais ficam como AJUSTE.
    """
    __tablename__ = "movimentacoes_estoque"

    id = Column(Integer, primary_key=True, index=True)
    estoque_id = Column(Integer, ForeignKey("estoques.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(
        SQLEnum(TipoMovimentacaoEstoque, name="tipo_mov_estoque_enum"),
        nullable=False,
    )
    quantidade = Column(Integer, nullable=False)
    motivo = Column(String(255), nullable=True)
    responsavel_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=False)

    estoque = relationship("Estoque", back_populates="movimentacoes")
    responsavel = relationship("Usuario", back_populates="movimentacoes_estoque")
    pedido = relationship("Pedido", back_populates="movimentacoes_estoque")


# ----------------------------------------------------------------------
# Pedidos e itens
# ----------------------------------------------------------------------

class Pedido(Base):
    """
    Pedido feito por um cliente em uma unidade, atraves de algum canal.
    O canalPedido eh OBRIGATORIO conforme requisito de multicanalidade.
    """
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    canal_pedido = Column(
        SQLEnum(CanalPedido, name="canal_pedido_enum"),
        nullable=False,
    )
    status = Column(
        SQLEnum(StatusPedido, name="status_pedido_enum"),
        nullable=False,
        default=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    metodo_pagamento = Column(
        SQLEnum(MetodoPagamento, name="metodo_pagamento_enum"),
        nullable=False,
        default=MetodoPagamento.MOCK,
    )
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    desconto = Column(Numeric(10, 2), nullable=False, default=0)
    total = Column(Numeric(10, 2), nullable=False, default=0)
    pontos_resgatados = Column(Integer, nullable=False, default=0)
    pontos_creditados = Column(Integer, nullable=False, default=0)
    promocao_id = Column(Integer, ForeignKey("promocoes.id"), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=False)
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    cliente = relationship("Usuario", back_populates="pedidos", foreign_keys=[cliente_id])
    unidade = relationship("Unidade", back_populates="pedidos")
    promocao = relationship("Promocao", back_populates="pedidos")
    itens = relationship(
        "ItemPedido", back_populates="pedido", cascade="all, delete-orphan"
    )
    pagamentos = relationship(
        "Pagamento", back_populates="pedido", cascade="all, delete-orphan"
    )
    movimentacoes_estoque = relationship("MovimentacaoEstoque", back_populates="pedido")
    movimentacoes_pontos = relationship("MovimentacaoPontos", back_populates="pedido")

    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_pedido_subtotal_nao_negativo"),
        CheckConstraint("total >= 0", name="ck_pedido_total_nao_negativo"),
        CheckConstraint("pontos_resgatados >= 0", name="ck_pedido_pontos_resg_nao_neg"),
    )


class ItemPedido(Base):
    """Linha de item dentro de um pedido. Guarda snapshot do preco."""
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal_item = Column(Numeric(10, 2), nullable=False)

    pedido = relationship("Pedido", back_populates="itens")
    produto = relationship("Produto", back_populates="itens_pedido")

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_item_qtd_positiva"),
        CheckConstraint("preco_unitario >= 0", name="ck_item_preco_nao_negativo"),
    )


# ----------------------------------------------------------------------
# Pagamentos (com mock)
# ----------------------------------------------------------------------

class Pagamento(Base):
    """
    Tentativa de pagamento de um pedido. Pode haver mais de uma por
    pedido (caso a primeira seja recusada e o cliente tente de novo).
    O processamento eh feito por um servico externo simulado (mock).
    """
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    metodo = Column(
        SQLEnum(MetodoPagamento, name="metodo_pagamento_enum"),
        nullable=False,
    )
    status = Column(
        SQLEnum(StatusPagamento, name="status_pagamento_enum"),
        nullable=False,
        default=StatusPagamento.PENDENTE,
    )
    referencia_externa = Column(String(100), nullable=True)
    payload_resposta = Column(Text, nullable=True)
    tentativas = Column(Integer, nullable=False, default=1)
    criado_em = Column(DateTime, server_default=func.now(), nullable=False)
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    pedido = relationship("Pedido", back_populates="pagamentos")


# ----------------------------------------------------------------------
# Fidelidade
# ----------------------------------------------------------------------

class PontosFidelidade(Base):
    """Saldo atual de pontos de um cliente. Uma linha por cliente."""
    __tablename__ = "pontos_fidelidade"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    saldo = Column(Integer, nullable=False, default=0)
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    cliente = relationship("Usuario", back_populates="pontos_fidelidade")

    __table_args__ = (
        CheckConstraint("saldo >= 0", name="ck_pontos_saldo_nao_negativo"),
    )


class MovimentacaoPontos(Base):
    """Historico de creditos, resgates e ajustes de pontos."""
    __tablename__ = "movimentacoes_pontos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(
        SQLEnum(TipoMovimentacaoPontos, name="tipo_mov_pontos_enum"),
        nullable=False,
    )
    pontos = Column(Integer, nullable=False)
    descricao = Column(String(255), nullable=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=False)

    cliente = relationship("Usuario", back_populates="movimentacoes_pontos")
    pedido = relationship("Pedido", back_populates="movimentacoes_pontos")


# ----------------------------------------------------------------------
# Promocoes
# ----------------------------------------------------------------------

class Promocao(Base):
    """
    Cupom ou campanha. No MVP fica como tabela simples; as regras de
    aplicacao sao calculadas no service de pedido.
    """
    __tablename__ = "promocoes"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    descricao = Column(String(255), nullable=True)
    percentual_desconto = Column(Numeric(5, 2), nullable=True)
    valor_desconto = Column(Numeric(10, 2), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    valido_de = Column(DateTime, nullable=True)
    valido_ate = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=False)

    pedidos = relationship("Pedido", back_populates="promocao")


# ----------------------------------------------------------------------
# Auditoria
# ----------------------------------------------------------------------

class LogAuditoria(Base):
    """
    Registro de acoes sensiveis. Atende o requisito de
    rastreabilidade exigido pelo roteiro e parte da LGPD.
    """
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    acao = Column(String(100), nullable=False)
    recurso = Column(String(100), nullable=True)
    recurso_id = Column(String(100), nullable=True)
    dados = Column(Text, nullable=True)
    ip_origem = Column(String(45), nullable=True)
    criado_em = Column(DateTime, server_default=func.now(), nullable=False)

    usuario = relationship("Usuario", back_populates="logs_auditoria")
