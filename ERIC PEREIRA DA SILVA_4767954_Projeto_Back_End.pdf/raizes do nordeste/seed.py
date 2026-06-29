"""
Atalho pra rodar o seed direto da raiz do projeto.

Uso:
    python seed.py
"""
from app.infrastructure.database.seed import rodar_seed


if __name__ == "__main__":
    rodar_seed()
