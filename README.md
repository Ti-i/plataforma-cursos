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

- Cadastro administrativo (CRUD) de instrutores, alunos, cursos, módulos e inscrições, com catálogo de instrutores, cursos e módulos de leitura pública.
- Inscrição de alunos em cursos (um aluno em vários cursos, um curso com vários alunos), com bloqueio de inscrição duplicada e em curso inativo.
- Acompanhamento de conclusão, com data de conclusão automática.
- Relatórios gerenciais prontos: alunos em cursos ativos, cursos com mais de 10 concluintes, carga horária por instrutor, alunos em mais de um curso e módulos de um curso em ordem.
- Login por token JWT, permissões por perfil (aluno e staff) e documentação Swagger gerada automaticamente.

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
python manage.py createsuperuser   # conta administrativa local (credenciais escolhidas por você)
python manage.py runserver
```

Blocos `bash` são para **Bash/Git Bash** (no Windows, use o Git Bash); o bloco `powershell` é para o **PowerShell**.

Acesse `http://127.0.0.1:8000/api/docs/`. O seed cria contas de **aluno** para demonstração: **`aluno1` / `senha12345`**.

Para testar o que é exclusivo de administração (escrita no catálogo, CRUD de alunos e de inscrições, relatórios), crie uma conta administrativa local com:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

O comando pergunta `username`, `e-mail` e `senha` — **as credenciais são escolhidas por você**. Não registre a senha em arquivos ou no Git; o Django armazena seu hash no banco local. Não use a conta `aluno1` para os relatórios: ela é uma aluna e recebe `403` nessas rotas.

**PostgreSQL (opcional):** no `.env`, defina `DB_ENGINE=postgres` e os dados `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`; instale o driver com `pip install psycopg2-binary`.

## 5. Autenticação

1. `POST /api/auth/login/` com `{"username": "aluno1", "password": "senha12345"}` devolve `access` e `refresh`.
2. No Swagger, clique em **Authorize** e informe `Bearer <access>`; em outros clientes, use o cabeçalho `Authorization: Bearer <access>`.
3. `POST /api/auth/refresh/` renova o `access`.

Regra: leitura do catálogo de instrutores, cursos e módulos é pública; escrita exige `is_staff=True`. Inscrições e relatórios exigem autenticação, e a maioria das operações sobre eles é restrita ao staff.

### Perfis e permissões

| Recurso | Visitante | Aluno (não-staff) | Staff |
|---|---|---|---|
| Instrutores, cursos e módulos — `GET` | ✅ | ✅ | ✅ |
| Instrutores, cursos e módulos — `POST`/`PUT`/`PATCH`/`DELETE` | 401 | 403 | ✅ |
| `GET /api/cursos/{id}/modulos/` | ✅ | ✅ | ✅ |
| `POST /api/cursos/{id}/inscrever/` | 401 | ✅ (usa o próprio perfil) | 403 se não tiver perfil de aluno |
| Alunos — listar, criar e excluir | 401 | 403 | ✅ |
| Alunos — detalhe, `PUT` e `PATCH` | 401 | apenas o próprio perfil (outro → 404) | ✅ qualquer perfil |
| Inscrições — listar e detalhar | 401 | apenas as próprias (outra → 404) | ✅ todas |
| Inscrições — criar, alterar, excluir e marcar conclusão | 401 | 403 | ✅ |
| Quatro relatórios | 401 | 403 | ✅ |

- **Contas de alunos** são criadas pelo administrador em `POST /api/alunos/` (com `username` e `password`); o aluno não pode criar, listar nem excluir alunos.
- **Inscrição do aluno** é feita exclusivamente pela action `POST /api/cursos/{id}/inscrever/`, que ignora qualquer aluno enviado no payload e usa o perfil vinculado ao usuário autenticado. Duplicidade e curso inativo continuam bloqueados.
- **Staff sem perfil de aluno** recebe `403` na action `inscrever`, mas pode cadastrar e gerenciar inscrições pelo CRUD administrativo `/api/inscricoes/`, inclusive marcar/desmarcar conclusão.
- No próprio perfil, o aluno pode alterar `nome`, `email` e `password` (write-only, com hash). Campos como `user`, `is_staff` e `is_superuser` não fazem parte do serializer e são ignorados.

## 6. Documentação da API

Resumo das rotas, filtros e exemplos em [`docs/API.md`](docs/API.md). Esquema OpenAPI em [`docs/openapi.yaml`](docs/openapi.yaml).

As quatro rotas de relatório exigem conta com `is_staff=True` (a de módulos, `/api/cursos/{id}/modulos/`, é pública):

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

**48 testes** cobrem, em resumo:

- **autenticação e permissões**: login válido e inválido; leitura pública do catálogo; escrita em instrutores, cursos e módulos só para staff; aluno não lista, não cria e não exclui alunos; aluno consulta e edita apenas o próprio perfil (outro perfil responde `404`, inclusive em tentativa de trocar a senha); campos de vínculo e privilégio são ignorados no payload; os quatro relatórios são restritos ao staff; usuário autenticado sem perfil de aluno recebe `403` (não `500`).
- **isolamento por usuário**: aluno vê somente as próprias inscrições (detalhe de terceiro responde `404`), não cria/altera/exclui inscrições pelo CRUD e não marca a própria conclusão; a action `inscrever` usa sempre o perfil do usuário logado; staff sem perfil de aluno recebe `403` nessa action.
- **operações CRUD**: criação, listagem, detalhe, atualização (PATCH e, nos cursos, PUT) e exclusão de instrutores, alunos, cursos, módulos e inscrições, executadas com autenticação de staff.
- **filtros e busca**: `?search=` em instrutores, alunos e cursos; `?ativo=` e `?instrutor=` em cursos; `?curso=` em módulos; `?aluno=`, `?curso=` e `?concluido=` em inscrições;
- **regras de inscrição e conclusão**: bloqueio de inscrição duplicada e em curso inativo, inscrição pela ação `inscrever` e preenchimento/limpeza da data de conclusão;
- **integridade, exclusão em cascata e relatórios**: ordem de módulo única por curso, proteção de instrutor com cursos, remoção em cascata de módulos e inscrições ao excluir um curso, e as cinco consultas do enunciado;
- **regressão**: `AlunoViewSet.get_queryset` retorna queryset vazio (sem exceção) quando não há usuário autenticado.

Os testes de acesso negado também conferem que os dados não foram alterados. A suíte cobre os fluxos principais da API, mas não representa cobertura total do código nem substitui uma revisão de segurança.

## 9. Requisitos

**Funcionais**

- RF01. Cadastrar, listar, atualizar e remover instrutores, alunos, cursos, módulos e inscrições (escrita restrita ao staff; leitura do catálogo pública).
- RF02. Inscrever aluno em curso ativo, sem duplicidade.
- RF03. Marcar inscrição como concluída, registrando a data (operação do staff).
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

- Permissões em dois níveis (aluno e staff); não há papel separado de instrutor nem permissões por objeto além do próprio perfil e das próprias inscrições.
- `Aluno.email` e o e-mail do `User` são campos independentes: editar o e-mail do aluno não sincroniza o e-mail da conta de login.
- Listagens sem paginação.
- Sem tela (front-end); a interação é pela API e pelo Swagger.
- Conclusão do curso é marcada manualmente, sem rastrear progresso por módulo.

**Próximos passos**

- Papel de instrutor com escopo próprio sobre os cursos que ministra.
- Progresso por módulo e conclusão automática do curso.
- Paginação, certificado de conclusão em PDF, avaliações de curso.
- Deploy com PostgreSQL e integração contínua.
