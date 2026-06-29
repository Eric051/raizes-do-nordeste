"""
Script de seed: popula o banco com dados iniciais pra rodar a API
sem precisar cadastrar tudo na mao.

Cria:
- 1 admin, 1 gerente, 1 atendente, 1 cozinha e 1 cliente
- 3 unidades (Recife, Belo Horizonte, Sao Paulo)
- 10 produtos do cardapio nordestino
- Cardapio de cada unidade (todos os produtos disponiveis)
- Estoque inicial em todas as unidades
- 1 promocao de exemplo (CUSCUZ20)

Eh idempotente: se algum registro ja existir (ex.: pelo email),
ele eh ignorado e nao duplica.

Uso direto:
    python seed.py
"""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.entities.enums import (
    CategoriaProduto,
    PerfilUsuario,
)
from app.infrastructure.database.connection import SessionLocal, engine, Base
from app.infrastructure.database import models
from app.infrastructure.security.password_hasher import hash_senha


def _criar_usuarios(db: Session) -> None:
    """Cadastra os usuarios padrao se ainda nao existirem."""
    usuarios = [
        {
            "nome": "Administrador do Sistema",
            "email": "admin@raizes.com",
            "senha": "Admin@123",
            "perfil": PerfilUsuario.ADMIN,
            "consentimento": True,
        },
        {
            "nome": "Gerente Recife Boa Viagem",
            "email": "gerente.recife@raizes.com",
            "senha": "Gerente@123",
            "perfil": PerfilUsuario.GERENTE,
            "consentimento": True,
        },
        {
            "nome": "Atendente Recife",
            "email": "atendente.recife@raizes.com",
            "senha": "Atendente@123",
            "perfil": PerfilUsuario.ATENDENTE,
            "consentimento": True,
        },
        {
            "nome": "Cozinha Recife",
            "email": "cozinha.recife@raizes.com",
            "senha": "Cozinha@123",
            "perfil": PerfilUsuario.COZINHA,
            "consentimento": True,
        },
        {
            "nome": "Maria da Silva",
            "email": "cliente@exemplo.com",
            "senha": "Cliente@123",
            "perfil": PerfilUsuario.CLIENTE,
            "consentimento": True,
            "cpf": "12345678900",
        },
    ]

    for u in usuarios:
        existente = db.query(models.Usuario).filter_by(email=u["email"]).first()
        if existente:
            continue
        usuario = models.Usuario(
            nome=u["nome"],
            email=u["email"],
            senha_hash=hash_senha(u["senha"]),
            perfil=u["perfil"],
            consentimento_lgpd=u.get("consentimento", False),
            data_consentimento=datetime.now(timezone.utc) if u.get("consentimento") else None,
            cpf=u.get("cpf"),
            ativo=True,
        )
        db.add(usuario)
        # se for cliente, ja cria o registro de pontos com saldo zero
        if usuario.perfil == PerfilUsuario.CLIENTE:
            db.flush()  # pra pegar o id do usuario
            db.add(models.PontosFidelidade(cliente_id=usuario.id, saldo=0))
    db.commit()


def _criar_unidades(db: Session) -> list[models.Unidade]:
    """Cria 3 unidades de exemplo."""
    dados = [
        {"nome": "Raizes Recife - Boa Viagem", "cidade": "Recife", "estado": "PE",
         "endereco": "Av. Boa Viagem, 1234"},
        {"nome": "Raizes BH - Pampulha", "cidade": "Belo Horizonte", "estado": "MG",
         "endereco": "Av. Antonio Carlos, 5678"},
        {"nome": "Raizes Sao Paulo - Centro", "cidade": "Sao Paulo", "estado": "SP",
         "endereco": "Rua 25 de Marco, 100"},
    ]

    unidades = []
    for d in dados:
        existente = db.query(models.Unidade).filter_by(nome=d["nome"]).first()
        if existente:
            unidades.append(existente)
            continue
        unidade = models.Unidade(**d, ativo=True)
        db.add(unidade)
        unidades.append(unidade)
    db.commit()
    for u in unidades:
        db.refresh(u)
    return unidades


def _criar_produtos(db: Session) -> list[models.Produto]:
    """Cria os produtos do cardapio."""
    dados = [
        ("Tapioca de Queijo Coalho", "Tapioca recheada com queijo coalho artesanal",
         Decimal("12.50"), CategoriaProduto.TAPIOCA, False),
        ("Tapioca de Carne de Sol", "Tapioca recheada com carne de sol e manteiga de garrafa",
         Decimal("18.90"), CategoriaProduto.TAPIOCA, False),
        ("Cuscuz com Manteiga de Garrafa", "Cuscuz tradicional com manteiga de garrafa",
         Decimal("9.00"), CategoriaProduto.CUSCUZ, False),
        ("Cuscuz Recheado de Frango", "Cuscuz com frango desfiado e queijo",
         Decimal("16.50"), CategoriaProduto.CUSCUZ, False),
        ("Bolo de Macaxeira", "Bolo de macaxeira (mandioca) com coco",
         Decimal("7.50"), CategoriaProduto.BOLO, False),
        ("Suco de Caju", "Suco natural de caju gelado, 300ml",
         Decimal("8.00"), CategoriaProduto.BEBIDA, False),
        ("Suco de Caja", "Suco natural de caja gelado, 300ml",
         Decimal("8.00"), CategoriaProduto.BEBIDA, False),
        ("Cafe Coado", "Cafe coado na hora, 80ml",
         Decimal("4.00"), CategoriaProduto.CAFE_DA_MANHA, False),
        ("Cafe com Leite", "Cafe com leite, 200ml",
         Decimal("6.00"), CategoriaProduto.CAFE_DA_MANHA, False),
        ("Bolo de Milho Junino", "Bolo de milho cremoso, disponivel so em junho",
         Decimal("10.00"), CategoriaProduto.BOLO, True),
    ]

    produtos = []
    for nome, descricao, preco, categoria, sazonal in dados:
        existente = db.query(models.Produto).filter_by(nome=nome).first()
        if existente:
            produtos.append(existente)
            continue
        produto = models.Produto(
            nome=nome,
            descricao=descricao,
            preco_base=preco,
            categoria=categoria,
            sazonal=sazonal,
            ativo=True,
        )
        db.add(produto)
        produtos.append(produto)
    db.commit()
    for p in produtos:
        db.refresh(p)
    return produtos


def _vincular_cardapio_e_estoque(
    db: Session,
    unidades: list[models.Unidade],
    produtos: list[models.Produto],
) -> None:
    """Coloca todos os produtos em todas as unidades e cria estoque inicial."""
    for unidade in unidades:
        for produto in produtos:
            # cardapio
            cardapio = (
                db.query(models.CardapioUnidade)
                .filter_by(unidade_id=unidade.id, produto_id=produto.id)
                .first()
            )
            if not cardapio:
                # produtos sazonais ficam indisponiveis fora de epoca
                disponivel = not produto.sazonal
                db.add(
                    models.CardapioUnidade(
                        unidade_id=unidade.id,
                        produto_id=produto.id,
                        disponivel=disponivel,
                        preco_local=None,
                    )
                )

            # estoque inicial: 50 unidades de cada
            estoque = (
                db.query(models.Estoque)
                .filter_by(unidade_id=unidade.id, produto_id=produto.id)
                .first()
            )
            if not estoque:
                db.add(
                    models.Estoque(
                        unidade_id=unidade.id,
                        produto_id=produto.id,
                        quantidade=50,
                    )
                )
    db.commit()


def _criar_promocoes(db: Session) -> None:
    """Cria uma promocao de exemplo."""
    existente = db.query(models.Promocao).filter_by(codigo="CUSCUZ20").first()
    if existente:
        return
    db.add(
        models.Promocao(
            codigo="CUSCUZ20",
            descricao="20% de desconto em qualquer cuscuz",
            percentual_desconto=Decimal("20.00"),
            ativo=True,
        )
    )
    db.commit()


def rodar_seed() -> None:
    """Funcao principal. Cria as tabelas e popula tudo."""
    # garante que as tabelas existem
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("[seed] criando usuarios...")
        _criar_usuarios(db)
        print("[seed] criando unidades...")
        unidades = _criar_unidades(db)
        print("[seed] criando produtos...")
        produtos = _criar_produtos(db)
        print("[seed] vinculando cardapio e estoque...")
        _vincular_cardapio_e_estoque(db, unidades, produtos)
        print("[seed] criando promocoes...")
        _criar_promocoes(db)
        print("[seed] concluido com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    rodar_seed()
