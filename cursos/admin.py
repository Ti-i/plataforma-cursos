from django.contrib import admin

from .models import Aluno, Curso, Inscricao, Instrutor, Modulo

admin.site.register([Instrutor, Aluno, Curso, Modulo, Inscricao])
