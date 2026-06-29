"""
Excecoes de dominio.

A ideia eh ter um conjunto de excecoes "de negocio" que os services
levantam quando uma regra eh violada, e os handlers da camada de API
traduzem essas excecoes pra responses HTTP padronizadas.

Assim eu nao espalho HTTPException do FastAPI pelos services e mantenho
o dominio independente do framework web.
"""


class DominioError(Exception):
    """Base de todas as excecoes do dominio."""
    error_code: str = "ERRO_DOMINIO"
    http_status: int = 400

    def __init__(self, message: str, details: list | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class RecursoNaoEncontrado(DominioError):
    error_code = "RECURSO_NAO_ENCONTRADO"
    http_status = 404


class CredenciaisInvalidas(DominioError):
    error_code = "CREDENCIAIS_INVALIDAS"
    http_status = 401


class SemPermissao(DominioError):
    error_code = "SEM_PERMISSAO"
    http_status = 403


class DadosInvalidos(DominioError):
    error_code = "DADOS_INVALIDOS"
    http_status = 422


class ConflitoDeNegocio(DominioError):
    """Usado quando a operacao nao pode ser feita por regra de negocio.
    Exemplos: estoque insuficiente, transicao de status invalida."""
    error_code = "CONFLITO_DE_NEGOCIO"
    http_status = 409


class EstoqueInsuficiente(ConflitoDeNegocio):
    error_code = "ESTOQUE_INSUFICIENTE"


class TransicaoInvalida(ConflitoDeNegocio):
    error_code = "TRANSICAO_DE_STATUS_INVALIDA"


class ConsentimentoLGPDNecessario(ConflitoDeNegocio):
    error_code = "CONSENTIMENTO_LGPD_NECESSARIO"


class FalhaIntegracaoExterna(DominioError):
    error_code = "FALHA_INTEGRACAO_EXTERNA"
    http_status = 502
