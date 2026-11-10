from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from .models import Aluno, Curso, Inscricao, Instrutor, Modulo


class InstrutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrutor
        fields = ["id", "nome", "email", "bio"]


class AlunoSerializer(serializers.ModelSerializer):
    # Usados apenas na criação: geram o usuário de login (relação 1:1)
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = Aluno
        fields = ["id", "nome", "email", "data_cadastro", "username", "password"]
        read_only_fields = ["data_cadastro"]

    def validate(self, attrs):
        if self.instance is None and not (attrs.get("username") and attrs.get("password")):
            raise serializers.ValidationError("Informe 'username' e 'password' para criar o aluno.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        username = validated_data.pop("username")
        password = validated_data.pop("password")
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError({"username": "Nome de usuário já existe."})
        user = User.objects.create_user(username=username, email=validated_data["email"], password=password)
        return Aluno.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("username", None)
        password = validated_data.pop("password", None)
        if password:
            instance.user.set_password(password)
            instance.user.save()
        return super().update(instance, validated_data)


class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = ["id", "curso", "titulo", "ordem"]


class CursoSerializer(serializers.ModelSerializer):
    instrutor_nome = serializers.CharField(source="instrutor.nome", read_only=True)

    class Meta:
        model = Curso
        fields = ["id", "titulo", "descricao", "carga_horaria", "ativo", "instrutor", "instrutor_nome"]


class InscricaoSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source="aluno.nome", read_only=True)
    curso_titulo = serializers.CharField(source="curso.titulo", read_only=True)

    class Meta:
        model = Inscricao
        fields = ["id", "aluno", "aluno_nome", "curso", "curso_titulo",
                  "data_inscricao", "concluido", "data_conclusao"]
        read_only_fields = ["data_inscricao", "data_conclusao"]

    def validate(self, attrs):
        curso = attrs.get("curso") or getattr(self.instance, "curso", None)
        # Só bloqueia novas inscrições; atualizar (ex.: concluir) um curso depois desativado é permitido
        if self.instance is None and curso and not curso.ativo:
            raise serializers.ValidationError("Não é possível se inscrever em um curso inativo.")
        return attrs


# ----- Serializers apenas de documentação dos relatórios (Swagger) -----

class InscricaoAtivaRelatorioSerializer(serializers.Serializer):
    aluno__nome = serializers.CharField()
    curso__titulo = serializers.CharField()
    data_inscricao = serializers.DateField()


class ConcluintesRelatorioSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    titulo = serializers.CharField()
    concluintes = serializers.IntegerField()


class CargaHorariaRelatorioSerializer(serializers.Serializer):
    nome = serializers.CharField()
    carga_total = serializers.IntegerField()


class AlunoMultiplosCursosRelatorioSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    total_cursos = serializers.IntegerField()
