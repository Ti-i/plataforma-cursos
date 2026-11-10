# Plataforma de Cursos Online

API REST em **Python + Django** para uma startup de educação gerenciar **cursos, instrutores, alunos, módulos e inscrições**. Projeto Integrador Back-End.

- **Autor:** Luís Flávio Viana Tavares (projeto individual)
- **Repositório:** https://github.com/Ti-i/plataforma-cursos
- **Documentação interativa (Swagger):** `http://127.0.0.1:8000/api/docs/` (com o servidor rodando)

## Sumário

1. [Problema e solução](#1-problema-e-solução)
2. [Tecnologias](#2-tecnologias)
3. [Arquitetura](#3-arquitetura)
4. [Instalação e execução](#4-instalação-e-execução)
5. [Autenticação](#5-autenticação)
6. [Documentação da API](#6-documentação-da-api)
7. [Banco de dados](#7-banco-de-dados)
8. [Testes](#8-testes)
9. [Requisitos](#9-requisitos)
10. [Como o projeto foi conduzido](#10-como-o-projeto-foi-conduzido)
11. [Limitações e próximos passos](#11-limitações-e-próximos-passos)

## 1. Problema e solução

Uma startup de educação precisa de uma plataforma para oferecer cursos online e guardar, de forma organizada, quem ensina, quem estuda e em que cursos cada aluno está inscrito. Sem um sistema, é difícil saber quais cursos estão ativos, quantos alunos concluíram cada um e qual a carga de trabalho de cada instrutor.

A API entrega:

- Cadastro completo (CRUD) de instrutores, alunos, cursos, módulos e inscrições.
- Inscrição de alunos em cursos (um aluno em vários cursos, um curso com vários alunos), com bloqueio de inscrição duplicada e em curso inativo.
- Acompanhamento de conclusão, com data de conclusão automática.
- Relatórios gerenciais prontos: alunos em cursos ativos, cursos com mais de 10 concluintes, carga horária por instrutor, alunos em mais de um curso e módulos de um curso em ordem.
- Login por token JWT e documentação Swagger gerada automaticamente.

## 2. Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3.12 + Django | Framework web e ORM |
| Django REST Framework | API REST (serializers, viewsets, routers) |
| SimpleJWT | Autenticação por token JWT |
| drf-spectacular | Documentação OpenAPI/Swagger |
| django-filter | Filtros nas listagens |
| SQLite (padrão) / PostgreSQL (opcional) | Banco de dados |

## 3. Arquitetura

```
plataforma-cursos/
├── config/                  # Configuração do projeto (settings, urls raiz)
├── cursos/                  # App principal
│   ├── models.py            # Entidades e constraints (camada de dados)
│   ├── serializers.py       # Validação e transformação (camada de entrada/saída)
│   ├── views.py             # ViewSets (CRUD) e relatórios (camada de negócio/HTTP)
│   ├── urls.py              # Roteamento
│   ├── admin.py             # Django Admin
│   ├── tests.py             # Testes automatizados
│   └── management/commands/seed_dados.py   # Dados de demonstração
├── docs/                    # MER, documentação da API e OpenAPI
├── requirements.txt
├── .env.example
└── README.md
```

Fluxo de uma requisição: **URL → View/ViewSet → Serializer (validação) → Model/ORM → Banco**, com autenticação JWT aplicada antes da view.

## 4. Instalação e execução

Pré-requisito: Python 3.12 ou superior.

```bash
git clone <URL-DO-REPOSITORIO>
cd plataforma-cursos

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # opcional: sem .env, roda com SQLite
python manage.py migrate
python manage.py seed_dados        # dados de demonstração
python manage.py createsuperuser   # opcional: acesso ao /admin/
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/api/docs/`. Usuário de demonstração criado pelo seed: **`aluno1` / `senha12345`**.

**PostgreSQL (opcional):** no `.env`, defina `DB_ENGINE=postgres` e os dados `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`; instale o driver com `pip install psycopg2-binary`.

## 5. Autenticação

1. `POST /api/auth/login/` com `{"username": "aluno1", "password": "senha12345"}` devolve `access` e `refresh`.
2. No Swagger, clique em **Authorize** e informe `Bearer <access>`; em outros clientes, use o cabeçalho `Authorization: Bearer <access>`.
3. `POST /api/auth/refresh/` renova o `access`.

Regra: leitura dos cadastros é pública; escrita, inscrições e relatórios exigem login.

## 6. Documentação da API

Resumo das rotas, filtros e exemplos em [`docs/API.md`](docs/API.md). Esquema OpenAPI em [`docs/openapi.yaml`](docs/openapi.yaml).

| Consulta do enunciado | Rota |
|---|---|
| Aluno, curso e data de inscrição em cursos ativos | `GET /api/relatorios/inscricoes-cursos-ativos/` |
| Cursos com mais de 10 concluintes | `GET /api/relatorios/cursos-concluintes/` |
| Instrutor e carga horária total | `GET /api/relatorios/carga-horaria-instrutor/` |
| Alunos inscritos em mais de um curso | `GET /api/relatorios/alunos-multiplos-cursos/` |
| Módulos de um curso em ordem | `GET /api/cursos/{id}/modulos/` |

## 7. Banco de dados

Diagrama MER, dicionário de dados e regras de integridade em [`docs/MER.md`](docs/MER.md).

Relacionamentos implementados: **1:1** (Usuário–Aluno), **1:N** (Instrutor–Curso, Curso–Módulo) e **N:N** (Aluno–Curso, via `Inscricao`). Constraints de unicidade impedem inscrição duplicada e módulos com a mesma ordem no mesmo curso.

## 8. Testes

```bash
python manage.py test
```

33 testes cobrem, em resumo:

- **autenticação e permissões**: login válido e inválido, leitura pública de cursos, escrita, relatórios e listagem de inscrições exigindo login, e bloqueio da ação `inscrever` para usuário sem perfil de aluno;
- **operações CRUD**: criação, listagem, detalhe, atualização (PATCH e, nos cursos, PUT) e exclusão de instrutores, alunos, cursos, módulos e inscrições;
- **filtros e busca**: `?search=` em instrutores, alunos e cursos; `?ativo=` e `?instrutor=` em cursos; `?curso=` em módulos; `?aluno=`, `?curso=` e `?concluido=` em inscrições;
- **regras de inscrição e conclusão**: bloqueio de inscrição duplicada e em curso inativo, inscrição pela ação `inscrever` e preenchimento/limpeza da data de conclusão;
- **integridade, exclusão em cascata e relatórios**: ordem de módulo única por curso, proteção de instrutor com cursos, remoção em cascata de módulos e inscrições ao excluir um curso, e as cinco consultas do enunciado.

## 9. Requisitos

**Funcionais**

- RF01. Cadastrar, listar, atualizar e remover instrutores, alunos, cursos, módulos e inscrições.
- RF02. Inscrever aluno em curso ativo, sem duplicidade.
- RF03. Marcar inscrição como concluída, registrando a data.
- RF04. Listar módulos de um curso em ordem sequencial.
- RF05. Emitir os relatórios gerenciais descritos na seção 6.

**Não funcionais**

- RNF01. Segurança: autenticação JWT, senhas com hash, segredos em variáveis de ambiente.
- RNF02. Integridade: constraints no banco e validações na API.
- RNF03. Documentação: Swagger/OpenAPI automático.
- RNF04. Manutenibilidade: separação em models, serializers, views e urls; testes automatizados.
- RNF05. Desempenho: `select_related` e agregações no banco, evitando consultas repetidas.
- RNF06. Portabilidade: SQLite por padrão, PostgreSQL por configuração.

## 10. Como o projeto foi conduzido

Projeto **individual**. Fluxo adotado: leitura do enunciado e da ficha de avaliação, modelagem (MER), implementação dos models e do CRUD, regras de negócio e relatórios, autenticação, testes, documentação.

Uso de IA: utilizei um assistente de IA como apoio para estruturar a modelagem, gerar código-base e testes e revisar a documentação. Todo o código foi lido, executado e validado por mim com a suíte de testes e o Swagger.

_Complete com links do quadro de tarefas (Trello/GitHub Projects), se tiver._

## 11. Limitações e próximos passos

**Limitações**

- Sem perfis de permissão (qualquer usuário autenticado pode alterar cadastros).
- Listagens sem paginação.
- Sem tela (front-end); a interação é pela API e pelo Swagger.
- Conclusão do curso é marcada manualmente, sem rastrear progresso por módulo.

**Próximos passos**

- Perfis (aluno, instrutor, administrador) com permissões por papel.
- Progresso por módulo e conclusão automática do curso.
- Paginação, certificado de conclusão em PDF, avaliações de curso.
- Deploy com PostgreSQL e integração contínua.
