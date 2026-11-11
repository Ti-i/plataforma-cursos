# Documentação da API

Documentação interativa (Swagger): `http://127.0.0.1:8000/api/docs/`
Esquema OpenAPI exportado: [`openapi.yaml`](openapi.yaml)

## Autenticação (JWT)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/auth/login/` | Recebe `username` e `password`; devolve `access` e `refresh` |
| POST | `/api/auth/refresh/` | Recebe `refresh`; devolve novo `access` |

Envie o token em todas as requisições protegidas: `Authorization: Bearer <access>`.

Regra geral: **leitura do catálogo de instrutores, cursos e módulos é pública**; **escrita é restrita a `is_staff=True`**. Inscrições e relatórios exigem autenticação.

## Permissões por perfil

| Operação | Visitante | Aluno (não-staff) | Staff |
|---|---|---|---|
| Instrutores, cursos e módulos — `GET` | ✅ | ✅ | ✅ |
| Instrutores, cursos e módulos — `POST`/`PUT`/`PATCH`/`DELETE` | 401 | 403 | ✅ |
| `GET /api/cursos/{id}/modulos/` | ✅ | ✅ | ✅ |
| `POST /api/cursos/{id}/inscrever/` | 401 | ✅ (próprio perfil) | 403 se não tiver perfil de aluno |
| Alunos — listar, criar e excluir | 401 | 403 | ✅ |
| Alunos — detalhe, `PUT` e `PATCH` | 401 | só o próprio perfil (outro → 404) | ✅ qualquer perfil |
| Inscrições — listar e detalhar | 401 | só as próprias (outra → 404) | ✅ todas |
| Inscrições — criar, alterar, excluir e concluir | 401 | 403 | ✅ |
| Quatro relatórios | 401 | 403 | ✅ |

## Contas

- **Contas de aluno são criadas pelo administrador** em `POST /api/alunos/`, informando `username` e `password` junto com os dados do aluno. O aluno não pode criar, listar nem excluir alunos; pode consultar e editar apenas o próprio perfil.
- **Conta administrativa local** (acesso ao Django Admin e às operações de staff):

  ```powershell
  .\.venv\Scripts\python.exe manage.py createsuperuser
  ```

  O comando pergunta `username`, `e-mail` e `senha`. **As credenciais são escolhidas por você**. Não registre a senha em arquivos ou no Git; o Django armazena seu hash no banco local. Não use a conta de demonstração `aluno1` para operações administrativas.
- **Staff sem perfil de aluno** recebe `403` na action `inscrever`, mas pode cadastrar, alterar, excluir e concluir inscrições pelo CRUD administrativo em `/api/inscricoes/`.

## CRUD

Cada recurso aceita `GET` (lista), `POST`, `GET /{id}/`, `PUT`, `PATCH` e `DELETE`, respeitando as permissões acima (escrita somente staff, exceto a edição do próprio perfil de aluno).

| Recurso | Rota base | Filtros / busca | Escrita |
|---|---|---|---|
| Instrutores | `/api/instrutores/` | `?search=` | staff |
| Alunos | `/api/alunos/` | `?search=` | staff (aluno edita só o próprio perfil) |
| Cursos | `/api/cursos/` | `?ativo=true`, `?instrutor=1`, `?search=` | staff |
| Módulos | `/api/modulos/` | `?curso=1` | staff |
| Inscrições | `/api/inscricoes/` | `?aluno=1`, `?curso=1`, `?concluido=true` | staff (aluno só lê as próprias) |

No próprio perfil, o aluno pode alterar `nome`, `email` e `password` (`write_only`, com hash). Campos como `user`, `is_staff` e `is_superuser` não fazem parte do serializer e são ignorados no payload.

## Rotas especiais

| Método | Rota | Descrição | Acesso |
|---|---|---|---|
| GET | `/api/cursos/{id}/modulos/` | **Consulta 5**: módulos do curso em ordem sequencial | público |
| POST | `/api/cursos/{id}/inscrever/` | Inscreve no curso o aluno vinculado ao usuário autenticado | aluno autenticado |

A action `inscrever` ignora qualquer aluno enviado no payload, bloqueia inscrição duplicada e curso inativo e devolve `403` para usuário sem perfil de aluno (inclusive staff).

## Relatórios (consultas do enunciado)

Todos exigem conta com `is_staff=True` (`401` sem token, `403` para aluno).

| # | Consulta | Rota |
|---|---|---|
| 1 | Aluno, curso e data de inscrição em cursos **ativos** | `GET /api/relatorios/inscricoes-cursos-ativos/` |
| 2 | Cursos com **mais de 10 concluintes** (ajustável com `?min=`) | `GET /api/relatorios/cursos-concluintes/` |
| 3 | Instrutor e **carga horária total** dos seus cursos | `GET /api/relatorios/carga-horaria-instrutor/` |
| 4 | Alunos inscritos em **mais de um curso** | `GET /api/relatorios/alunos-multiplos-cursos/` |
| 5 | Módulos de "Introdução a Bancos de Dados" em ordem | `GET /api/cursos/{id}/modulos/` |

## Códigos de resposta

`200` ok · `201` criado · `204` removido · `400` validação · `401` sem token / token inválido · `403` autenticado sem permissão (aluno em rota de staff, staff sem perfil de aluno na action `inscrever`) · `404` não encontrado (inclui perfil ou inscrição de outro usuário) · `409` conflito (instrutor com cursos).

## Exemplos (curl)

Os exemplos usam **Bash/Git Bash** (no Windows, execute no Git Bash), com o virtualenv ativado:

```bash
source .venv/Scripts/activate   # Windows (Git Bash); no Linux/macOS: source .venv/bin/activate
```

### Demonstração como aluno

Conta criada pelo seed:

```bash
TOKEN_ALUNO=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"aluno1","password":"senha12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")

# lista apenas as inscrições do próprio aluno1
curl -H "Authorization: Bearer $TOKEN_ALUNO" http://127.0.0.1:8000/api/inscricoes/

# inscreve o aluno1 no curso 1; se o seed já inscreveu esse aluno nesse curso,
# a resposta é 400 (inscrição duplicada), o que é esperado
curl -X POST -H "Authorization: Bearer $TOKEN_ALUNO" http://127.0.0.1:8000/api/cursos/1/inscrever/
```

### Demonstração como administrador

Conta criada por você com `createsuperuser`:

```bash
# variáveis de shell (não são variáveis de ambiente; não há export)
ADMIN_USER="<usuario-que-voce-criou>"
read -r -s -p "Senha do administrador: " ADMIN_PASS
echo

TOKEN_ADMIN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" \
  | python -c "import sys,json;print(json.load(sys.stdin)['access'])")

# relatórios e escrita no catálogo exigem esse token de staff
curl -H "Authorization: Bearer $TOKEN_ADMIN" http://127.0.0.1:8000/api/relatorios/cursos-concluintes/
```

Não registre a senha em arquivos ou no Git; o Django armazena seu hash no banco local.

`aluno1` recebe `403` nos relatórios e em qualquer escrita administrativa.
