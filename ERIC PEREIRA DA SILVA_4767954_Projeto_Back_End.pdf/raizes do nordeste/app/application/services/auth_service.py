"""
Service de autenticacao.

Cuida do cadastro de cliente e do login. As regras estao aqui no service
e os contratos (request/response) ficam no schemas/auth.py.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UsuarioResponse,
)
from app.domain.entities.enums import PerfilUsuario
from app.domain.exceptions import (
    ConflitoDeNegocio,
    ConsentimentoLGPDNecessario,
    CredenciaisInvalidas,
    DadosInvalidos,
)
from app.domain.regras.lgpd import mascarar_cpf, normalizar_cpf
from app.infrastructure.audit.audit_logger import registrar_log
from app.infrastructure.database import models
from app.infrastructure.security.jwt_handler import criar_token
from app.infrastructure.security.password_hasher import hash_senha, verificar_senha


def montar_resposta_usuario(usuario: models.Usuario) -> UsuarioResponse:
    """Monta o UsuarioResponse a partir do model. Sem senha, com CPF mascarado."""
    return UsuarioResponse(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        perfil=usuario.perfil,
        consentimento_lgpd=usuario.consentimento_lgpd,
        cpf_mascarado=mascarar_cpf(usuario.cpf),
        ativo=usuario.ativo,
        criado_em=usuario.criado_em,
    )


def cadastrar_cliente(db: Session, dados: RegisterRequest) -> UsuarioResponse:
    """
    Cadastra um cliente novo. Outros perfis (admin, gerente etc) nao
    da pra cadastrar por aqui, tem que ser via endpoint admin (que
    deixei pra implementar depois se precisar).

    Validacoes:
      - exige consentimento LGPD
      - email unico (case insensitive)
      - cpf unico, se vier
    """
    if not dados.consentimento_lgpd:
        raise ConsentimentoLGPDNecessario(
            "Eh necessario aceitar o termo de tratamento de dados pra criar conta.",
            details=[{"field": "consentimento_lgpd", "issue": "obrigatorio aceitar"}],
        )

    email_lower = dados.email.lower().strip()
    if db.query(models.Usuario).filter_by(email=email_lower).first():
        raise ConflitoDeNegocio(
            "Ja existe um usuario com esse e-mail.",
            details=[{"field": "email", "issue": "ja cadastrado"}],
        )

    cpf_limpo = normalizar_cpf(dados.cpf)
    if cpf_limpo:
        if len(cpf_limpo) != 11:
            raise DadosInvalidos(
                "CPF invalido.",
                details=[{"field": "cpf", "issue": "deve ter 11 digitos"}],
            )
        if db.query(models.Usuario).filter_by(cpf=cpf_limpo).first():
            raise ConflitoDeNegocio(
                "Ja existe um usuario com esse CPF.",
                details=[{"field": "cpf", "issue": "ja cadastrado"}],
            )

    usuario = models.Usuario(
        nome=dados.nome.strip(),
        email=email_lower,
        senha_hash=hash_senha(dados.senha),
        cpf=cpf_limpo,
        perfil=PerfilUsuario.CLIENTE,
        consentimento_lgpd=True,
        data_consentimento=datetime.now(timezone.utc),
        ativo=True,
    )
    db.add(usuario)
    db.flush()  # pra ter o id antes do commit

    # ja deixa o registro de pontos zerado pro novo cliente
    db.add(models.PontosFidelidade(cliente_id=usuario.id, saldo=0))

    registrar_log(
        db,
        acao="USUARIO_CADASTRADO",
        usuario_id=usuario.id,
        recurso="USUARIO",
        recurso_id=usuario.id,
        dados={
            "perfil": usuario.perfil.value,
            "consentimento_lgpd": usuario.consentimento_lgpd,
        },
    )

    db.commit()
    db.refresh(usuario)

    return montar_resposta_usuario(usuario)


def fazer_login(db: Session, dados: LoginRequest) -> TokenResponse:
    """
    Login. Valida email e senha e devolve um JWT.

    A mensagem de erro eh igual pra "email nao existe" e "senha errada"
    de proposito, pra atacante nao descobrir quais emails existem.
    """
    email_lower = dados.email.lower().strip()
    usuario = db.query(models.Usuario).filter_by(email=email_lower).first()

    if not usuario or not usuario.ativo:
        raise CredenciaisInvalidas("E-mail ou senha invalidos.")

    if not verificar_senha(dados.senha, usuario.senha_hash):
        raise CredenciaisInvalidas("E-mail ou senha invalidos.")

    registrar_log(
        db,
        acao="LOGIN",
        usuario_id=usuario.id,
        recurso="USUARIO",
        recurso_id=usuario.id,
        dados={"perfil": usuario.perfil.value},
        commit=True,
    )

    token, expires_in = criar_token(usuario.id, usuario.perfil.value)
    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=expires_in,
        usuario=montar_resposta_usuario(usuario),
    )
