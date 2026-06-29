"""
Hash e verificacao de senhas usando bcrypt diretamente.

Antes eu usava passlib como wrapper, mas ele esta sem manutencao e gera
warnings com versoes novas do bcrypt. Como o bcrypt direto eh simples
de usar, vale a pena ir nele e remover a dependencia.
"""
import bcrypt


# bcrypt tem um limite tecnico de 72 bytes na senha. Senhas maiores que
# isso sao truncadas silenciosamente, o que pode virar bug se um usuario
# pos uma senha gigante. Pra evitar surpresa, eu trunco explicitamente.
_LIMITE_BCRYPT_BYTES = 72


def _preparar_senha(senha: str) -> bytes:
    senha_bytes = senha.encode("utf-8")
    if len(senha_bytes) > _LIMITE_BCRYPT_BYTES:
        senha_bytes = senha_bytes[:_LIMITE_BCRYPT_BYTES]
    return senha_bytes


def hash_senha(senha_em_texto: str) -> str:
    """Gera o hash bcrypt de uma senha em texto plano."""
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(_preparar_senha(senha_em_texto), salt)
    return hash_bytes.decode("utf-8")


def verificar_senha(senha_em_texto: str, hash_armazenado: str) -> bool:
    """Compara uma senha digitada com o hash armazenado no banco."""
    try:
        return bcrypt.checkpw(
            _preparar_senha(senha_em_texto),
            hash_armazenado.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # se o hash estiver corrompido ou em formato invalido, falha o login
        return False
