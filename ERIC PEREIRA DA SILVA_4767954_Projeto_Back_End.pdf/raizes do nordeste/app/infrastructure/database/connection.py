"""
Configuracao do SQLAlchemy.

Aqui criamos o engine, a SessionLocal (fabrica de sessoes) e a Base
que os modelos vao herdar. Tambem expoe o get_db() que eh a dependency
do FastAPI pra abrir e fechar sessoes a cada request.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings


# O SQLite precisa de check_same_thread=False, senao o FastAPI reclama
# quando varias requisicoes compartilham a sessao em paralelo.
# Outros bancos nao precisam disso.
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False  # se quiser ver as queries no console, troca pra True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Todos os modelos SQLAlchemy vao herdar dessa Base
Base = declarative_base()


def get_db():
    """
    Dependency do FastAPI. Cada request abre uma sessao do banco e
    garante que ela vai ser fechada no final, mesmo se der erro.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
