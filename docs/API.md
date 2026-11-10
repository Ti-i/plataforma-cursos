# Documentação da API

Documentação interativa (Swagger): `http://127.0.0.1:8000/api/docs/`
Esquema OpenAPI exportado: [`openapi.yaml`](openapi.yaml)

## Autenticação (JWT)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/auth/login/` | Recebe `username` e `password`; devolve `access` e `refresh` |
| POST | `/api/auth/refresh/` | Recebe `refresh`; devolve novo `access` |

Envie o token em todas as requisições protegidas: `Authorization: Bearer <access>`.
Regra geral: **leitura (GET) é pública** nos cadastros; **escrita exige login**. Inscrições e relatórios exigem login sempre.

## CRUD

Cada recurso aceita `GET` (lista), `POST`, `GET /{id}/`, `PUT`, `PATCH` e `DELETE`.

| Recurso | Rota base | Filtros / busca |
|---|---|---|
| Instrutores | `/api/instrutores/` | `?search=` |
| Alunos | `/api/alunos/` | `?search=` |
| Cursos | `/api/cursos/` | `?ativo=true`, `?instrutor=1`, `?search=` |
| Módulos | `/api/modulos/` | `?curso=1` |
| Inscrições | `/api/inscricoes/` | `?aluno=1`, `?curso=1`, `?concluido=true` |

## Rotas especiais

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/cursos/{id}/modulos/` | **Consulta 5**: módulos do curso em ordem sequencial |
| POST | `/api/cursos/{id}/inscrever/` | Inscreve o aluno logado no curso |

## Relatórios (consultas do enunciado)

Todos exigem login.

| # | Consulta | Rota |
|---|---|---|
| 1 | Aluno, curso e data de inscrição em cursos **ativos** | `GET /api/relatorios/inscricoes-cursos-ativos/` |
| 2 | Cursos com **mais de 10 concluintes** (ajustável com `?min=`) | `GET /api/relatorios/cursos-concluintes/` |
| 3 | Instrutor e **carga horária total** dos seus cursos | `GET /api/relatorios/carga-horaria-instrutor/` |
| 4 | Alunos inscritos em **mais de um curso** | `GET /api/relatorios/alunos-multiplos-cursos/` |
| 5 | Módulos de "Introdução a Bancos de Dados" em ordem | `GET /api/cursos/{id}/modulos/` |

## Códigos de resposta

`200` ok · `201` criado · `204` removido · `400` validação · `401` sem token / token inválido · `403` usuário não é aluno · `404` não encontrado · `409` conflito (instrutor com cursos).

## Exemplo rápido (curl)

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"aluno1","password":"senha12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/relatorios/cursos-concluintes/
```
