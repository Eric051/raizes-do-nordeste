"""
Utilitarios pra cumprir a LGPD.

Aqui tem funcoes simples de mascaramento e normalizacao de dados
sensiveis, usadas pelos services e handlers da API antes de devolver
dados em respostas.
"""


def mascarar_cpf(cpf: str | None) -> str | None:
    """
    Mascara o CPF pra exibir em respostas e listagens.

    Exemplo: 12345678900 -> 123.***.***-00

    Se o CPF nao tiver 11 digitos depois de limpar, devolve a string
    original mesmo (pra nao mascarar errado um valor invalido).
    """
    if not cpf:
        return None
    cpf_limpo = "".join(c for c in cpf if c.isdigit())
    if len(cpf_limpo) != 11:
        return cpf
    return f"{cpf_limpo[:3]}.***.***-{cpf_limpo[-2:]}"


def normalizar_cpf(cpf: str | None) -> str | None:
    """
    Tira pontuacao e espacos do CPF, deixando so os digitos.
    Devolve None se a string vier vazia.
    """
    if not cpf:
        return None
    so_digitos = "".join(c for c in cpf if c.isdigit())
    return so_digitos or None
