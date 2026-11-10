"""Permissões reutilizáveis da API de cursos."""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Leitura (GET/HEAD/OPTIONS) pública; escrita apenas para is_staff=True."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class IsSelfOrStaff(BasePermission):
    """Objeto: liberado para o próprio dono (perfil Aluno) ou para staff."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_staff or getattr(obj, "user_id", None) == user.id)
        )


class HasAlunoProfile(BasePermission):
    """Exige perfil Aluno; staff passa mesmo sem perfil (administra inscrições)."""

    message = "Seu usuário não é um aluno."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_staff or getattr(user, "aluno", None) is not None)
        )
