from django.db.models import Count, Q, ProtectedError, Sum
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aluno, Curso, Inscricao, Instrutor, Modulo
from .serializers import (
    AlunoMultiplosCursosRelatorioSerializer, AlunoSerializer, CargaHorariaRelatorioSerializer,
    ConcluintesRelatorioSerializer, CursoSerializer, InscricaoAtivaRelatorioSerializer,
    InscricaoSerializer, InstrutorSerializer, ModuloSerializer,
)


# ----------------------------- CRUD -----------------------------

class InstrutorViewSet(viewsets.ModelViewSet):
    queryset = Instrutor.objects.all()
    serializer_class = InstrutorSerializer
    search_fields = ["nome", "email"]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Não é possível remover um instrutor que ainda possui cursos."},
                status=status.HTTP_409_CONFLICT,
            )


class AlunoViewSet(viewsets.ModelViewSet):
    queryset = Aluno.objects.all()
    serializer_class = AlunoSerializer
    search_fields = ["nome", "email"]


class CursoViewSet(viewsets.ModelViewSet):
    queryset = Curso.objects.select_related("instrutor")
    serializer_class = CursoSerializer
    filterset_fields = ["ativo", "instrutor"]
    search_fields = ["titulo", "descricao"]

    @extend_schema(responses=inline_serializer(
        name="ModulosDoCurso",
        fields={"curso": serializers.CharField(), "modulos": ModuloSerializer(many=True)},
    ))
    @action(detail=True, methods=["get"])
    def modulos(self, request, pk=None):
        """Consulta 5: módulos do curso em ordem sequencial."""
        curso = self.get_object()
        modulos = ModuloSerializer(curso.modulos.order_by("ordem"), many=True).data
        return Response({"curso": curso.titulo, "modulos": modulos})

    @extend_schema(request=None, responses={201: InscricaoSerializer})
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def inscrever(self, request, pk=None):
        """Inscreve o aluno logado neste curso."""
        curso = self.get_object()
        aluno = getattr(request.user, "aluno", None)
        if aluno is None:
            return Response({"detail": "Seu usuário não é um aluno."}, status=status.HTTP_403_FORBIDDEN)
        serializer = InscricaoSerializer(data={"aluno": aluno.pk, "curso": curso.pk})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ModuloViewSet(viewsets.ModelViewSet):
    queryset = Modulo.objects.select_related("curso")
    serializer_class = ModuloSerializer
    filterset_fields = ["curso"]


class InscricaoViewSet(viewsets.ModelViewSet):
    queryset = Inscricao.objects.select_related("aluno", "curso")
    serializer_class = InscricaoSerializer
    filterset_fields = ["aluno", "curso", "concluido"]
    permission_classes = [IsAuthenticated]


# ------------------- Relatórios (consultas complexas) -------------------

class InscricoesCursosAtivosView(APIView):
    """Consulta 1: aluno, curso e data de inscrição de quem está em cursos ativos."""
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=InscricaoAtivaRelatorioSerializer(many=True))
    def get(self, request):
        qs = (Inscricao.objects.filter(curso__ativo=True)
              .select_related("aluno", "curso")
              .order_by("curso__titulo", "aluno__nome")
              .values("aluno__nome", "curso__titulo", "data_inscricao"))
        return Response(list(qs))


class CursosConcluintesView(APIView):
    """Consulta 2: cursos com mais de N concluintes (padrão: 10)."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("min", OpenApiTypes.INT, description="Mínimo exclusivo de concluintes (padrão 10)")],
        responses=ConcluintesRelatorioSerializer(many=True),
    )
    def get(self, request):
        try:
            minimo = int(request.query_params.get("min", 10))
        except ValueError:
            return Response({"detail": "'min' deve ser um número inteiro."}, status=status.HTTP_400_BAD_REQUEST)
        qs = (Curso.objects
              .annotate(concluintes=Count("inscricoes", filter=Q(inscricoes__concluido=True)))
              .filter(concluintes__gt=minimo)
              .order_by("-concluintes")
              .values("id", "titulo", "concluintes"))
        return Response(list(qs))


class CargaHorariaInstrutorView(APIView):
    """Consulta 3: nome do instrutor e carga horária total dos cursos que ministra."""
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=CargaHorariaRelatorioSerializer(many=True))
    def get(self, request):
        qs = (Instrutor.objects
              .annotate(carga_total=Sum("cursos__carga_horaria"))
              .order_by("nome")
              .values("nome", "carga_total"))
        return Response(list(qs))


class AlunosMultiplosCursosView(APIView):
    """Consulta 4: alunos inscritos em mais de um curso."""
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=AlunoMultiplosCursosRelatorioSerializer(many=True))
    def get(self, request):
        qs = (Aluno.objects
              .annotate(total_cursos=Count("inscricoes"))
              .filter(total_cursos__gt=1)
              .order_by("-total_cursos", "nome")
              .values("id", "nome", "total_cursos"))
        return Response(list(qs))
