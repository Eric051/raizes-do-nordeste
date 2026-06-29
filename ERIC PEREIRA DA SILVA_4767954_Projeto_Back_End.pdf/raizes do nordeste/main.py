"""
Ponto de entrada da API Raizes do Nordeste.

Cria a aplicacao FastAPI, registra os endpoints, configura o
ciclo de vida pra criar as tabelas no startup, registra os
handlers globais de erro e enriquece o Swagger/OpenAPI com
tags, descricoes e logins de teste.

Pra rodar:
    uvicorn main:app --reload

Apos subir, abre http://localhost:8000/docs pra ver o Swagger.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.error_handlers import registrar_handlers
from app.api.routes import auditoria as auditoria_routes
from app.api.routes import auth as auth_routes
from app.api.routes import cardapio as cardapio_routes
from app.api.routes import estoque as estoque_routes
from app.api.routes import fidelidade as fidelidade_routes
from app.api.routes import pagamentos as pagamentos_routes
from app.api.routes import pedidos as pedidos_routes
from app.api.routes import produtos as produtos_routes
from app.api.routes import unidades as unidades_routes
from app.config import settings
from app.infrastructure.database.connection import engine, Base
# o import abaixo registra todos os modelos na Base antes do create_all.
# Sem isso, o SQLAlchemy nao sabe quais tabelas precisa criar.
from app.infrastructure.database import models  # noqa: F401


# ----------------------------------------------------------------------
# Metadados pro Swagger/OpenAPI
# ----------------------------------------------------------------------

TAGS_METADATA = [
    {
        "name": "Saude",
        "description": "Endpoints simples pra checar se a API esta no ar.",
    },
    {
        "name": "Autenticacao",
        "description": (
            "Cadastro de cliente, login e consulta do usuario "
            "atualmente autenticado."
        ),
    },
    {
        "name": "Unidades",
        "description": "Cadastro e gestao das lojas da rede.",
    },
    {
        "name": "Produtos",
        "description": "Catalogo geral. Cada unidade tem seu proprio cardapio.",
    },
    {
        "name": "Cardapio",
        "description": "Cardapio especifico de cada unidade.",
    },
    {
        "name": "Estoque",
        "description": "Saldos e movimentacoes por unidade.",
    },
    {
        "name": "Pedidos",
        "description": (
            "Pedidos com canal de origem (canalPedido eh OBRIGATORIO, "
            "valores: APP, TOTEM, BALCAO, PICKUP, WEB)."
        ),
    },
    {
        "name": "Pagamentos",
        "description": (
            "Integracao com gateway de pagamento simulado (mock). "
            "O pedido nao trafega dados de cartao."
        ),
    },
    {
        "name": "Fidelidade",
        "description": (
            "Programa de pontos. 1 ponto a cada R$ 1,00 gasto, "
            "1 ponto vale R$ 0,10 de desconto."
        ),
    },
    {
        "name": "Auditoria",
        "description": "Logs de acoes sensiveis (somente ADMIN).",
    },
]


DESCRICAO = """
API back-end da rede de lanchonetes nordestinas **Raizes do Nordeste**.

Projeto multidisciplinar do curso de Analise e Desenvolvimento de Sistemas
da UNINTER, trilha Back-End, ano 2026.

## Como autenticar

1. Faz `POST /auth/login` com `email` e `senha`.
2. Copia o `access_token` da resposta.
3. Clica no botao **Authorize** (cadeado, no topo da pagina) e cola o token.
4. Pronto, todos os endpoints autenticados funcionam.

### Logins de teste (criados pelo seed)

| E-mail                          | Senha          | Perfil    |
|---------------------------------|----------------|-----------|
| admin@raizes.com                | Admin@123      | ADMIN     |
| gerente.recife@raizes.com       | Gerente@123    | GERENTE   |
| atendente.recife@raizes.com     | Atendente@123  | ATENDENTE |
| cozinha.recife@raizes.com       | Cozinha@123    | COZINHA   |
| cliente@exemplo.com             | Cliente@123    | CLIENTE   |

## Padrao de erro

Todos os erros saem no mesmo formato JSON:

```json
{
  "error": "ESTOQUE_INSUFICIENTE",
  "message": "Estoque insuficiente para um ou mais itens.",
  "details": [{"field": "itens[0].quantidade", "issue": "..."}],
  "timestamp": "2026-04-30T12:00:00Z",
  "path": "/pedidos"
}
```

## Codigos de status usados

- **200 / 201 / 204** sucesso
- **400 / 422** dados invalidos
- **401** nao autenticado
- **403** sem permissao
- **404** recurso nao encontrado
- **409** conflito de regra de negocio (estoque, transicao de status, etc)
- **502** falha no gateway externo (pagamento)

## Fluxo principal (MVP)

1. Cliente faz login e olha o cardapio de uma unidade.
2. Cria um pedido informando `canal_pedido` e os itens.
3. Solicita o pagamento; o gateway mock devolve aprovado ou recusado.
4. Pedido vai pra `PAGO`, estoque eh baixado e pontos sao creditados.
5. Cozinha muda status pra `EM_PREPARO` -> `PRONTO`; atendente conclui em `ENTREGUE`.

Repositorio: https://github.com/lucas-quintanilha/raizes_do_nordeste_api
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan do FastAPI. Roda no startup (antes do yield) e no shutdown
    (depois do yield). Garante que as tabelas existem.
    """
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=DESCRICAO,
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "Lucas Quintanilha",
        "email": "lucas_sq@live.com",
    },
    lifespan=lifespan,
)

# handlers globais de erro pra que toda excecao saia no padrao JSON unico
registrar_handlers(app)

# rotas da aplicacao (ordem das tags no Swagger segue essa ordem)
app.include_router(auth_routes.router)
app.include_router(unidades_routes.router)
app.include_router(produtos_routes.router)
app.include_router(cardapio_routes.router)
app.include_router(estoque_routes.router)
app.include_router(pedidos_routes.router)
app.include_router(pagamentos_routes.router)
app.include_router(fidelidade_routes.router)
app.include_router(auditoria_routes.router)


@app.get("/", tags=["Saude"])
def root():
    """Endpoint raiz, so pra confirmar que a API esta no ar."""
    return {
        "aplicacao": settings.app_name,
        "versao": settings.app_version,
        "documentacao": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Saude"])
def health_check():
    """Health check simples, util pra validar se a API subiu."""
    return {"status": "ok"}
