"""Popula o banco com dados de demonstração: `python manage.py seed_dados`."""
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from cursos.models import Aluno, Curso, Inscricao, Instrutor, Modulo

SENHA_DEMO = "senha12345"

INSTRUTORES = [
    ("Ana Beatriz Lima", "ana@plataforma.dev", "Doutora em Bancos de Dados."),
    ("Carlos Eduardo Rocha", "carlos@plataforma.dev", "Engenheiro de software, foco em back-end."),
    ("Mariana Souza", "mariana@plataforma.dev", "Designer e desenvolvedora front-end."),
]

# (titulo, carga_horaria, ativo, indice_instrutor, modulos)
CURSOS = [
    ("Introdução a Bancos de Dados", 40, True, 0,
     ["Introdução", "Modelagem Entidade-Relacionamento", "SQL Básico", "SQL Avançado"]),
    ("Python para Back-End", 60, True, 1,
     ["Fundamentos de Python", "Django na prática", "APIs REST com DRF", "Autenticação JWT"]),
    ("Front-End Moderno", 50, True, 2, ["HTML e CSS", "JavaScript", "React"]),
    ("Git e GitHub", 20, True, 1, ["Controle de versão", "Branches e Pull Requests"]),
    ("Curso Descontinuado de Flash", 30, False, 2, ["Introdução"]),
]

NOMES = ["Luís", "Beatriz", "Rafael", "Camila", "Joana", "Pedro", "Larissa", "Mateus", "Isabela",
         "Gustavo", "Fernanda", "Bruno", "Aline", "Thiago", "Patrícia", "Diego"]


class Command(BaseCommand):
    help = "Cria instrutores, cursos, módulos, alunos e inscrições de exemplo."

    @transaction.atomic
    def handle(self, *args, **options):
        if Curso.objects.exists():
            self.stdout.write(self.style.WARNING("Já existem dados; seed ignorado."))
            return
        random.seed(42)  # resultados reproduzíveis

        instrutores = [Instrutor.objects.create(nome=n, email=e, bio=b) for n, e, b in INSTRUTORES]

        cursos = []
        for titulo, carga, ativo, idx, modulos in CURSOS:
            curso = Curso.objects.create(
                titulo=titulo, descricao=f"Curso de {titulo}.", carga_horaria=carga,
                ativo=ativo, instrutor=instrutores[idx],
            )
            for ordem, titulo_mod in enumerate(modulos, start=1):
                Modulo.objects.create(curso=curso, titulo=titulo_mod, ordem=ordem)
            cursos.append(curso)

        alunos = []
        for i, nome in enumerate(NOMES, start=1):
            username = f"aluno{i}"
            user = User.objects.create_user(username, f"{username}@email.com", SENHA_DEMO)
            alunos.append(Aluno.objects.create(user=user, nome=f"{nome} Silva", email=user.email))

        ativos = [c for c in cursos if c.ativo]
        for aluno in alunos:
            for curso in random.sample(ativos, k=random.choice([1, 1, 2, 3])):
                Inscricao.objects.create(aluno=aluno, curso=curso)
        # Garante >10 concluintes no primeiro curso (Consulta 2 retorna algo na demo)
        for aluno in alunos[:12]:
            insc, _ = Inscricao.objects.get_or_create(aluno=aluno, curso=cursos[0])
            insc.concluido = True
            insc.save()
        # Uma inscrição antiga em curso inativo, para a Consulta 1 provar o filtro
        Inscricao.objects.create(aluno=alunos[0], curso=cursos[-1])

        self.stdout.write(self.style.SUCCESS(
            f"Seed concluído: {len(instrutores)} instrutores, {len(cursos)} cursos, "
            f"{len(alunos)} alunos. Login demo: aluno1 / {SENHA_DEMO}"
        ))
