# Modelo Entidade-Relacionamento

```mermaid
erDiagram
    USER ||--|| ALUNO : "1:1 (login)"
    INSTRUTOR ||--o{ CURSO : ministra
    CURSO ||--o{ MODULO : "é dividido em"
    ALUNO ||--o{ INSCRICAO : realiza
    CURSO ||--o{ INSCRICAO : recebe

    USER {
        int id PK
        string username UK
        string password
    }
    INSTRUTOR {
        int id PK
        string nome
        string email UK
        text bio
    }
    ALUNO {
        int id PK
        int user_id FK, UK
        string nome
        string email UK
        date data_cadastro
    }
    CURSO {
        int id PK
        string titulo
        text descricao
        int carga_horaria
        bool ativo
        int instrutor_id FK
    }
    MODULO {
        int id PK
        int curso_id FK
        string titulo
        int ordem
    }
    INSCRICAO {
        int id PK
        int aluno_id FK
        int curso_id FK
        date data_inscricao
        bool concluido
        date data_conclusao
    }
```

## Relacionamentos

| Relação | Tipo | Implementação |
|---|---|---|
| Usuário ↔ Aluno | 1:1 | `Aluno.user` (`OneToOneField`) |
| Instrutor → Cursos | 1:N | `Curso.instrutor` (`ForeignKey`, `PROTECT`) |
| Curso → Módulos | 1:N | `Modulo.curso` (`ForeignKey`, `CASCADE`) |
| Aluno ↔ Curso | N:N | Tabela associativa `Inscricao` (`ManyToManyField(through=...)`) |

## Dicionário de dados

**Instrutor**: `nome` (texto, obrigatório), `email` (único), `bio` (opcional).

**Aluno**: `user` (login 1:1), `nome`, `email` (único), `data_cadastro` (automática).

**Curso**: `titulo`, `descricao`, `carga_horaria` (horas, inteiro positivo), `ativo` (padrão `true`), `instrutor` (obrigatório).

**Modulo**: `curso`, `titulo`, `ordem` (inteiro positivo).

**Inscricao**: `aluno`, `curso`, `data_inscricao` (automática), `concluido` (padrão `false`), `data_conclusao` (preenchida automaticamente ao concluir).

## Regras de integridade

- `Inscricao`: par (`aluno`, `curso`) **único**: ninguém se inscreve duas vezes no mesmo curso.
- `Modulo`: par (`curso`, `ordem`) **único**: não há dois módulos na mesma posição do curso.
- Não é possível **remover um instrutor** que ainda tenha cursos (`PROTECT`; a API responde 409).
- Remover um curso remove seus módulos e inscrições (`CASCADE`).
- Não é possível **criar inscrição** em curso inativo (validação na API).
