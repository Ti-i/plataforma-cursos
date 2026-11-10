from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("instrutores", views.InstrutorViewSet)
router.register("alunos", views.AlunoViewSet)
router.register("cursos", views.CursoViewSet)
router.register("modulos", views.ModuloViewSet)
router.register("inscricoes", views.InscricaoViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("relatorios/inscricoes-cursos-ativos/", views.InscricoesCursosAtivosView.as_view()),
    path("relatorios/cursos-concluintes/", views.CursosConcluintesView.as_view()),
    path("relatorios/carga-horaria-instrutor/", views.CargaHorariaInstrutorView.as_view()),
    path("relatorios/alunos-multiplos-cursos/", views.AlunosMultiplosCursosView.as_view()),
]
