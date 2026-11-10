from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Instrutor(models.Model):
    nome = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "instrutores"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Aluno(models.Model):
    # 1:1 com o usuário de autenticação do Django
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="aluno")
    nome = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    data_cadastro = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Curso(models.Model):
    titulo = models.CharField(max_length=150)
    descricao = models.TextField()
    carga_horaria = models.PositiveIntegerField(help_text="Carga horária em horas")
    ativo = models.BooleanField(default=True)
    # 1:N -> um instrutor ministra vários cursos; cada curso tem um único instrutor
    instrutor = models.ForeignKey(Instrutor, on_delete=models.PROTECT, related_name="cursos")
    # N:N -> alunos <-> cursos, intermediada pela tabela Inscricao
    alunos = models.ManyToManyField(Aluno, through="Inscricao", related_name="cursos")

    class Meta:
        ordering = ["titulo"]

    def __str__(self):
        return self.titulo


class Modulo(models.Model):
    # 1:N -> cada módulo pertence a um único curso
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="modulos")
    titulo = models.CharField(max_length=150)
    ordem = models.PositiveIntegerField()

    class Meta:
        ordering = ["curso", "ordem"]
        constraints = [
            models.UniqueConstraint(fields=["curso", "ordem"], name="modulo_ordem_unica_por_curso")
        ]

    def __str__(self):
        return f"{self.curso.titulo} - Módulo {self.ordem}: {self.titulo}"


class Inscricao(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="inscricoes")
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="inscricoes")
    data_inscricao = models.DateField(auto_now_add=True)
    concluido = models.BooleanField(default=False)
    data_conclusao = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "inscrição"
        verbose_name_plural = "inscrições"
        constraints = [
            models.UniqueConstraint(fields=["aluno", "curso"], name="inscricao_unica_aluno_curso")
        ]

    def save(self, *args, **kwargs):
        # Preenche a data de conclusão automaticamente ao marcar como concluído
        if self.concluido and not self.data_conclusao:
            self.data_conclusao = timezone.localdate()
        if not self.concluido:
            self.data_conclusao = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aluno} -> {self.curso}"
