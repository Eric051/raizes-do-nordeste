"""
Configuracao da aplicacao.

A ideia aqui eh ler as variaveis do .env e expor um objeto `settings`
unico que o resto do codigo importa quando precisa de algo configuravel.
Isso evita ficar espalhando os.getenv() pelo projeto e facilita testar.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Banco de dados
    database_url: str = "sqlite:///./raizes_do_nordeste.db"

    # JWT
    jwt_secret_key: str = "troque-isso-por-uma-chave-secreta-bem-grande-em-producao"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # Aplicacao
    app_name: str = "Raizes do Nordeste API"
    app_version: str = "1.0.0"
    debug: bool = True

    # Pagamento mock
    payment_mock_default_outcome: str = "APROVADO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# instancia unica que vai ser importada nos outros modulos
settings = Settings()
