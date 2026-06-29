Raízes do Nordeste API

API REST desenvolvida para o projeto Rede Raízes do Nordeste, atividade prática da disciplina Projeto Multidisciplinar – Trilha Back-End do curso de Análise e Desenvolvimento de Sistemas.

O sistema simula o gerenciamento de uma rede de lanchonetes especializadas em culinária nordestina, oferecendo recursos para administração de usuários, unidades, produtos, cardápios, estoque, pedidos, pagamentos e programa de fidelidade.

Objetivo

O objetivo deste projeto é desenvolver uma API Back-End utilizando boas práticas de arquitetura de software, permitindo o gerenciamento completo das operações da rede Raízes do Nordeste.

A aplicação foi construída utilizando FastAPI e SQLAlchemy, seguindo uma arquitetura organizada por camadas para facilitar manutenção, escalabilidade e reutilização do código.

Tecnologias Utilizadas
Python 3.11+
FastAPI
SQLAlchemy ORM
SQLite
JWT (Autenticação)
bcrypt
Pydantic
Uvicorn
Swagger UI
ReDoc
Estrutura do Projeto
raizes_do_nordeste/

│
├── app/
│   ├── api/
│   ├── core/
│   ├── database/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── security/
│   └── utils/
│
├── docs/
│
├── tests/
│
├── main.py
├── seed.py
├── requirements.txt
├── README.md
└── .env.example
Funcionalidades

O sistema contempla os seguintes módulos:

Cadastro de usuários
Autenticação por JWT
Controle de perfis de acesso
Cadastro de unidades
Cadastro de categorias
Cadastro de produtos
Gerenciamento de cardápio
Controle de estoque
Registro de clientes
Cadastro de pedidos
Atualização do status dos pedidos
Simulação de pagamento
Programa de fidelidade
Histórico de operações
Documentação automática da API
Organização do Código

A aplicação está dividida em camadas:

API

Responsável pelas rotas REST, validação dos dados e comunicação com o cliente.

Services

Implementa todas as regras de negócio do sistema.

Models

Define as entidades do banco de dados utilizando SQLAlchemy ORM.

Schemas

Modelos Pydantic utilizados para validação das requisições e respostas.

Database

Responsável pela configuração da conexão com o banco.

Security

Implementa autenticação JWT, criptografia de senhas e autorização.

Recursos Implementados

✔ CRUD de Usuários

✔ CRUD de Clientes

✔ CRUD de Produtos

✔ CRUD de Categorias

✔ CRUD de Unidades

✔ Controle de Estoque

✔ Controle de Cardápio

✔ Registro de Pedidos

✔ Atualização de Status

✔ Programa de Fidelidade

✔ Login com JWT

✔ Documentação Swagger

Como Executar

Clone o projeto:

git clone <repositorio>

Crie o ambiente virtual:

python -m venv venv

Ative o ambiente:

Windows

venv\Scripts\activate

Linux/Mac

source venv/bin/activate

Instale as dependências:

pip install -r requirements.txt

Execute a aplicação:

uvicorn main:app --reload
Documentação

Após iniciar o servidor, a documentação poderá ser acessada em:

Swagger

http://localhost:8000/docs

ReDoc

http://localhost:8000/redoc
Objetivos Atendidos
Modelagem do banco de dados
API REST
Persistência de dados
Autenticação e autorização
Controle de estoque
Gestão de pedidos
Programa de fidelidade
Integração simulada de pagamentos
Documentação automática
Desenvolvedor

Nome: Eric Pereira da Silva

Curso: Análise e Desenvolvimento de Sistemas

Instituição: UNINTER

Disciplina: Projeto Multidisciplinar – Trilha Back-End

Ano: 2026