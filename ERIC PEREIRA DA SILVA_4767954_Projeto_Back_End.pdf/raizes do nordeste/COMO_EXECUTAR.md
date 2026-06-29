# Como executar o projeto

Esse guia mostra como subir a API na sua máquina. Tentei deixar no nível de quem nunca rodou um projeto Python antes, então se você já manja, pula as partes óbvias.

> Esse arquivo vai sendo atualizado conforme o projeto cresce. O fluxo geral é o mesmo, mas cada etapa nova mexe num pouquinho.

## 1. O que precisa ter instalado

Antes de tudo:

* **Python 3.11 ou mais novo**. Pra confirmar se já tem, abre o terminal e digita `python --version` (no Windows também serve `py --version`). Se não tiver, baixa em https://www.python.org/downloads/. Importante mesmo: na hora da instalação, marca **Add Python to PATH**, senão o terminal não vai achar o python depois.
* **pip**. Vem junto com o Python.
* **Git**, opcional, só se for clonar. Pra ver se tem, `git --version`.

## 2. Pegar o código

Tem dois jeitos.

**Jeito 1, clonar pelo Git** (recomendado se for mexer no código):

```bash
git clone https://github.com/lucas-quintanilha/raizes_do_nordeste_api.git
cd raizes_do_nordeste_api
```

**Jeito 2, ZIP**:

Vai na página do repositório no GitHub, clica em "Code" e depois "Download ZIP". Extrai numa pasta qualquer e abre o terminal lá dentro.

## 3. Criar o venv

Venv (ambiente virtual) é tipo uma caixinha que isola as bibliotecas desse projeto das que você tem instaladas no Python global. É boa prática em qualquer projeto Python, evita conflito chato.

**Windows (PowerShell ou CMD):**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux ou macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

Quando ativar certo, o terminal vai mostrar `(venv)` no começo da linha. É assim que sabe que tá funcionando.

> Se aparecer aquele erro chato de "execution policy" no PowerShell do Windows, roda esse comando uma vez como Admin: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`. Depois ativa o venv normal.

## 4. Instalar as dependências

Com o venv ativo:

```bash
pip install -r requirements.txt
```

Demora um pouquinho na primeira vez. Se rolar erro de `bcrypt` no Windows, geralmente atualizar o pip resolve:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Configurar variáveis de ambiente

Copia o arquivo de exemplo:

**Windows:**

```bash
copy .env.example .env
```

**Linux ou macOS:**

```bash
cp .env.example .env
```

Abre o `.env` num editor. Pra rodar local não precisa mudar nada. Em produção real você ia querer trocar a `JWT_SECRET_KEY` por uma string aleatória forte, mas aqui pode deixar como tá.

## 6. Popular o banco com dados de teste (seed)

> Rodar isso é praticamente obrigatório, senão o banco fica vazio e não dá pra testar nada.

O seed cria:

* 5 usuários (admin, gerente, atendente, cozinha, cliente)
* 3 unidades (Recife, BH e SP)
* 10 produtos do cardápio nordestino
* Cardápio e estoque inicial em cada unidade
* 1 promoção ativa (código `CUSCUZ20`)

Pra rodar:

```bash
python seed.py
```

No terminal vai aparecer cada etapa do seed e no final o "[seed] concluido com sucesso.". Os logins criados:

| E-mail                          | Senha          | Perfil    |
|---------------------------------|----------------|-----------|
| admin@raizes.com                | Admin@123      | ADMIN     |
| gerente.recife@raizes.com       | Gerente@123    | GERENTE   |
| atendente.recife@raizes.com     | Atendente@123  | ATENDENTE |
| cozinha.recife@raizes.com       | Cozinha@123    | COZINHA   |
| cliente@exemplo.com             | Cliente@123    | CLIENTE   |

> O seed é idempotente. Pode rodar quantas vezes quiser que ele não duplica nada.

## 7. Subir a API

Já com tudo instalado e o seed rodado:

```bash
uvicorn main:app --reload
```

O `--reload` faz o servidor reiniciar quando você muda algum arquivo, o que ajuda muito pra desenvolver.

Se subiu certinho, vai aparecer mais ou menos isso:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

## 8. Testar se tá no ar

No navegador:

* Endpoint raiz: http://localhost:8000/
* Health check: http://localhost:8000/health
* Swagger (testar a API direto pelo navegador): http://localhost:8000/docs
* ReDoc (alternativa do swagger, mais bonitinho): http://localhost:8000/redoc

Pelo Swagger dá pra testar a API toda sem precisar do Postman.

### Como autenticar no Swagger

Quase todo endpoint pede token. Pra testar:

1. No Swagger, expande o `POST /auth/login`
2. Clica em "Try it out" e usa um login do seed (ex: `cliente@exemplo.com` / `Cliente@123`)
3. Manda o request e copia o `access_token` da resposta
4. Lá em cima da página tem um botão "Authorize" (cadeado). Clica nele.
5. Cola o token (sem o "Bearer " na frente, o swagger já põe) e confirma
6. Pronto, agora dá pra testar tudo

Pra cadastrar um cliente novo, usa `POST /auth/register` com email novo e `consentimento_lgpd: true`.

## 9. Parar a API

No terminal onde tá rodando, `Ctrl + C`. Pra desativar o venv depois, `deactivate`.

## 10. Banco de dados

Por padrão o sistema usa SQLite e cria o arquivo `raizes_do_nordeste.db` na raiz na primeira vez que sobe. Não precisa instalar nada.

Se quiser zerar e começar do zero, é só apagar esse arquivo e rodar o seed de novo.

> Pra olhar o banco visualmente recomendo o [DB Browser for SQLite](https://sqlitebrowser.org/). É gratuito e fácil.

## 11. Ver o DER

O DER fica em `docs/der.png`. Pra ver, é só abrir a imagem direto no explorer ou clicar no link no GitHub depois que subir o repositório.

Os outros diagramas (casos de uso, classes e sequência) também estão em `docs/` no formato PNG.

## 12. Coleção Postman

A coleção fica no `postman_collection.json` na raiz, com 18 testes (12 positivos e 6 negativos) cobrindo auth, validações, regra de negócio, pagamento mock e auditoria.

### Importar

1. Abre o Postman
2. **Import** (canto superior esquerdo)
3. Escolhe o `postman_collection.json`
4. A coleção **Raizes do Nordeste API** aparece na sidebar

A `baseUrl` já tá em `http://localhost:8000`. Se você subiu em outra porta, ajusta em **Variables** dentro da coleção.

### Antes de rodar

* API rodando (`uvicorn main:app --reload`)
* Seed executado pelo menos uma vez

### Rodar tudo de uma vez

Botão direito na coleção > **Run collection** > **Run Raizes do Nordeste API**. Os 18 testes rodam em ordem e ele mostra um relatório com PASS/FAIL.

> Os tokens (admin e cliente) e o `pedidoId` são capturados automaticamente entre os testes pelos scripts de teste, então não precisa copiar nada manualmente.

### Cobertura

Tá organizada em 5 pastas:

1. Autenticação: login admin, login cliente, login com senha errada (401)
2. Listagens: unidades, produtos, cardápio, listar sem token (401)
3. Pedidos: criar válido, sem canalPedido (422), produto inexistente (404), estoque insuficiente (409), cliente cria produto (403)
4. Pagamentos: aprovar via mock, criar outro pedido, recusar via mock
5. Fidelidade e Auditoria: saldo, cliente tenta auditoria (403), admin acessa auditoria (200)

### Editar a coleção

Se quiser mexer em algum teste, abre o `postman_collection.json` direto no Postman, ajusta o que precisar e exporta de novo por cima do arquivo. Não precisa de script nenhum.

## Problemas comuns

**"python não é reconhecido como comando":** Python não tá no PATH. Reinstala marcando "Add Python to PATH" ou usa `py` no Windows.

**"port 8000 já está em uso":** alguma coisa tá rodando ali. Sobe em outra porta com `uvicorn main:app --reload --port 8001`.

**"ModuleNotFoundError":** esqueceu de ativar o venv ou de instalar as dependências. Confere se aparece o `(venv)` no terminal e roda `pip install -r requirements.txt` de novo.

**Mudei o código mas nada acontece:** confirma que subiu com `--reload`. Se mesmo assim não atualiza, mata o processo (`Ctrl + C`) e sobe de novo.

**Erro estranho de banco:** quase sempre resolve apagando o `raizes_do_nordeste.db`, rodando `python seed.py` e subindo a API de novo. Se persistir, abre uma issue no repositório.
