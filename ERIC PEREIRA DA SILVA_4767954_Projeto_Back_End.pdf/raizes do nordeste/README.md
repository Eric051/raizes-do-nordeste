## Como Executar

### 1. Clone o repositório

```bash
git clone https://github.com/Eric051/raizes-do-nordeste.git
cd raizes-do-nordeste
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv
```

### 3. Ative o ambiente virtual

**Windows**

```bash
venv\Scripts\activate
```

**Linux/macOS**

```bash
source venv/bin/activate
```

### 4. Instale as dependências

```bash
pip install -r requirements.txt
```

### 5. Execute o seed (caso exista)

```bash
python seed.py
```

### 6. Inicie a API

```bash
uvicorn main:app --reload
```

A API ficará disponível em:

```
http://127.0.0.1:8000
```

## Documentação

Após iniciar o servidor, acesse:

### Swagger UI

```
http://127.0.0.1:8000/docs
```

### ReDoc

```
http://127.0.0.1:8000/redoc
```