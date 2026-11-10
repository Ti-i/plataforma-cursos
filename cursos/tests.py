from django.contrib.auth.models import AnonymousUser, User
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from .models import Aluno, Curso, Inscricao, Instrutor, Modulo
from .views import AlunoViewSet


class BaseTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instrutor = Instrutor.objects.create(nome="Ana", email="ana@x.com")
        cls.curso = Curso.objects.create(
            titulo="Introdução a Bancos de Dados", descricao="d", carga_horaria=40, instrutor=cls.instrutor)
        cls.inativo = Curso.objects.create(
            titulo="Antigo", descricao="d", carga_horaria=10, ativo=False, instrutor=cls.instrutor)
        cls.user = User.objects.create_user("luis", "luis@x.com", "senha12345")
        cls.aluno = Aluno.objects.create(user=cls.user, nome="Luis", email="luis@x.com")
        cls.staff = User.objects.create_user("staff", "staff@x.com", "senha12345", is_staff=True)

    def autenticar(self):
        resp = self.client.post("/api/auth/login/", {"username": "luis", "password": "senha12345"})
        self.assertEqual(resp.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def autenticar_staff(self):
        resp = self.client.post("/api/auth/login/", {"username": "staff", "password": "senha12345"})
        self.assertEqual(resp.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")


class AutenticacaoTests(BaseTestCase):
    def test_login_retorna_tokens(self):
        resp = self.client.post("/api/auth/login/", {"username": "luis", "password": "senha12345"})
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_login_invalido(self):
        resp = self.client.post("/api/auth/login/", {"username": "luis", "password": "errada"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_leitura_publica_mas_escrita_exige_login(self):
        self.assertEqual(self.client.get("/api/cursos/").status_code, 200)
        payload = {"titulo": "Novo", "descricao": "d", "carga_horaria": 10, "instrutor": self.instrutor.pk}
        self.assertEqual(self.client.post("/api/cursos/", payload).status_code, 401)
        self.autenticar()
        self.assertEqual(self.client.post("/api/cursos/", payload).status_code, 403)
        self.autenticar_staff()
        self.assertEqual(self.client.post("/api/cursos/", payload).status_code, 201)

    def test_relatorios_exigem_login(self):
        self.assertEqual(self.client.get("/api/relatorios/alunos-multiplos-cursos/").status_code, 401)


class CrudTests(BaseTestCase):
    def setUp(self):
        self.autenticar_staff()

    def test_crud_completo_de_curso(self):
        payload = {"titulo": "Django", "descricao": "d", "carga_horaria": 30, "instrutor": self.instrutor.pk}
        criado = self.client.post("/api/cursos/", payload)
        self.assertEqual(criado.status_code, 201)
        pk = criado.data["id"]
        self.assertEqual(self.client.get(f"/api/cursos/{pk}/").data["instrutor_nome"], "Ana")
        self.assertEqual(self.client.patch(f"/api/cursos/{pk}/", {"carga_horaria": 35}).data["carga_horaria"], 35)
        self.assertEqual(self.client.delete(f"/api/cursos/{pk}/").status_code, 204)

    def test_criar_aluno_cria_usuario_de_login(self):
        resp = self.client.post("/api/alunos/", {
            "nome": "Bia", "email": "bia@x.com", "username": "bia", "password": "senha12345"})
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.get(username="bia").check_password("senha12345"))
        self.assertNotIn("password", resp.data)

    def test_criar_aluno_sem_credenciais_falha(self):
        resp = self.client.post("/api/alunos/", {"nome": "Bia", "email": "bia@x.com"})
        self.assertEqual(resp.status_code, 400)

    def test_nao_remove_instrutor_com_cursos(self):
        resp = self.client.delete(f"/api/instrutores/{self.instrutor.pk}/")
        self.assertEqual(resp.status_code, 409)  # PROTECT impede apagar instrutor com cursos
        self.assertTrue(Instrutor.objects.filter(pk=self.instrutor.pk).exists())


class InscricaoTests(BaseTestCase):
    def setUp(self):
        self.autenticar_staff()

    def test_inscricao_em_curso_ativo(self):
        resp = self.client.post("/api/inscricoes/", {"aluno": self.aluno.pk, "curso": self.curso.pk})
        self.assertEqual(resp.status_code, 201)

    def test_bloqueia_inscricao_em_curso_inativo(self):
        resp = self.client.post("/api/inscricoes/", {"aluno": self.aluno.pk, "curso": self.inativo.pk})
        self.assertEqual(resp.status_code, 400)

    def test_bloqueia_inscricao_duplicada(self):
        Inscricao.objects.create(aluno=self.aluno, curso=self.curso)
        resp = self.client.post("/api/inscricoes/", {"aluno": self.aluno.pk, "curso": self.curso.pk})
        self.assertEqual(resp.status_code, 400)

    def test_acao_inscrever_usa_aluno_logado(self):
        self.autenticar()  # a ação é do aluno, não do staff
        resp = self.client.post(f"/api/cursos/{self.curso.pk}/inscrever/")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["aluno"], self.aluno.pk)

    def test_concluir_preenche_data_conclusao(self):
        insc = Inscricao.objects.create(aluno=self.aluno, curso=self.curso)
        resp = self.client.patch(f"/api/inscricoes/{insc.pk}/", {"concluido": True})
        self.assertTrue(resp.data["concluido"])
        self.assertIsNotNone(resp.data["data_conclusao"])


class ModeloTests(BaseTestCase):
    def test_ordem_de_modulo_unica_por_curso(self):
        Modulo.objects.create(curso=self.curso, titulo="M1", ordem=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Modulo.objects.create(curso=self.curso, titulo="Outro", ordem=1)


class RelatoriosTests(BaseTestCase):
    def setUp(self):
        self.autenticar_staff()
        # 12 alunos concluintes no curso principal
        for i in range(12):
            u = User.objects.create_user(f"u{i}", f"u{i}@x.com", "senha12345")
            a = Aluno.objects.create(user=u, nome=f"Aluno {i:02d}", email=u.email)
            Inscricao.objects.create(aluno=a, curso=self.curso, concluido=True)
        Inscricao.objects.create(aluno=self.aluno, curso=self.curso)
        Inscricao.objects.create(aluno=self.aluno, curso=self.inativo)
        Modulo.objects.create(curso=self.curso, titulo="Avançado", ordem=2)
        Modulo.objects.create(curso=self.curso, titulo="Introdução", ordem=1)

    def test_consulta1_somente_cursos_ativos(self):
        dados = self.client.get("/api/relatorios/inscricoes-cursos-ativos/").data
        self.assertEqual(len(dados), 13)
        self.assertTrue(all(d["curso__titulo"] == self.curso.titulo for d in dados))

    def test_consulta2_cursos_com_mais_de_10_concluintes(self):
        dados = self.client.get("/api/relatorios/cursos-concluintes/").data
        self.assertEqual([(d["titulo"], d["concluintes"]) for d in dados], [(self.curso.titulo, 12)])
        self.assertEqual(self.client.get("/api/relatorios/cursos-concluintes/?min=12").data, [])

    def test_consulta2_parametro_invalido(self):
        self.assertEqual(self.client.get("/api/relatorios/cursos-concluintes/?min=abc").status_code, 400)

    def test_consulta3_carga_horaria_total_do_instrutor(self):
        dados = self.client.get("/api/relatorios/carga-horaria-instrutor/").data
        self.assertEqual(dados, [{"nome": "Ana", "carga_total": 50}])

    def test_consulta4_alunos_em_mais_de_um_curso(self):
        dados = self.client.get("/api/relatorios/alunos-multiplos-cursos/").data
        self.assertEqual([(d["nome"], d["total_cursos"]) for d in dados], [("Luis", 2)])

    def test_consulta5_modulos_em_ordem(self):
        dados = self.client.get(f"/api/cursos/{self.curso.pk}/modulos/").data
        self.assertEqual([m["titulo"] for m in dados["modulos"]], ["Introdução", "Avançado"])


# ------------------- Cobertura complementar de CRUD e permissões -------------------

class InstrutorApiTests(BaseTestCase):
    def setUp(self):
        self.autenticar_staff()

    def test_crud_completo_de_instrutor(self):
        # search_fields = ["nome", "email"]
        busca = self.client.get("/api/instrutores/", {"search": "Ana"})
        self.assertEqual(busca.status_code, 200)
        self.assertEqual([i["nome"] for i in busca.data], ["Ana"])
        self.assertEqual(self.client.get("/api/instrutores/", {"search": "Carlos"}).data, [])

        detalhe = self.client.get(f"/api/instrutores/{self.instrutor.pk}/")
        self.assertEqual(detalhe.status_code, 200)
        self.assertEqual(detalhe.data["email"], "ana@x.com")

        criado = self.client.post("/api/instrutores/", {
            "nome": "Bruno", "email": "bruno@x.com", "bio": "Professor"})
        self.assertEqual(criado.status_code, 201)
        pk = criado.data["id"]
        self.assertTrue(Instrutor.objects.filter(pk=pk, nome="Bruno").exists())

        atualizado = self.client.patch(f"/api/instrutores/{pk}/", {"bio": "Coordenador"})
        self.assertEqual(atualizado.status_code, 200)
        self.assertEqual(Instrutor.objects.get(pk=pk).bio, "Coordenador")

        # instrutor sem cursos pode ser removido
        removido = self.client.delete(f"/api/instrutores/{pk}/")
        self.assertEqual(removido.status_code, 204)
        self.assertFalse(Instrutor.objects.filter(pk=pk).exists())


class AlunoApiTests(BaseTestCase):
    def setUp(self):
        self.autenticar_staff()

    def test_lista_detalhe_atualizacao_e_exclusao(self):
        # search_fields = ["nome", "email"]
        lista = self.client.get("/api/alunos/", {"search": "Luis"})
        self.assertEqual(lista.status_code, 200)
        self.assertEqual([a["id"] for a in lista.data], [self.aluno.pk])
        self.assertEqual(self.client.get("/api/alunos/", {"search": "Ninguem"}).data, [])

        detalhe = self.client.get(f"/api/alunos/{self.aluno.pk}/")
        self.assertEqual(detalhe.status_code, 200)
        self.assertEqual(detalhe.data["nome"], "Luis")
        self.assertEqual(detalhe.data["email"], "luis@x.com")

        atualizado = self.client.patch(f"/api/alunos/{self.aluno.pk}/", {"nome": "Luis Silva"})
        self.assertEqual(atualizado.status_code, 200)
        self.assertEqual(Aluno.objects.get(pk=self.aluno.pk).nome, "Luis Silva")

        excluido = self.client.delete(f"/api/alunos/{self.aluno.pk}/")
        self.assertEqual(excluido.status_code, 204)
        self.assertFalse(Aluno.objects.filter(pk=self.aluno.pk).exists())


class CursoApiTests(BaseTestCase):
    def setUp(self):
        self.autenticar_staff()

    def test_filtros_e_busca_de_cursos(self):
        # filterset_fields = ["ativo", "instrutor"]; search_fields = ["titulo", "descricao"]
        ativos = self.client.get("/api/cursos/", {"ativo": "true"})
        self.assertEqual([c["id"] for c in ativos.data], [self.curso.pk])

        inativos = self.client.get("/api/cursos/", {"ativo": "false"})
        self.assertEqual([c["id"] for c in inativos.data], [self.inativo.pk])

        por_instrutor = self.client.get("/api/cursos/", {"instrutor": self.instrutor.pk})
        self.assertEqual({c["id"] for c in por_instrutor.data}, {self.curso.pk, self.inativo.pk})

        busca = self.client.get("/api/cursos/", {"search": "Bancos"})
        self.assertEqual([c["id"] for c in busca.data], [self.curso.pk])

    def test_put_completo_de_curso(self):
        outro = Instrutor.objects.create(nome="Carla", email="carla@x.com")
        resp = self.client.put(f"/api/cursos/{self.curso.pk}/", {
            "titulo": "Bancos de Dados II", "descricao": "Avançado",
            "carga_horaria": 60, "ativo": False, "instrutor": outro.pk})
        self.assertEqual(resp.status_code, 200)
        curso = Curso.objects.get(pk=self.curso.pk)
        self.assertEqual(
            (curso.titulo, curso.descricao, curso.carga_horaria, curso.ativo),
            ("Bancos de Dados II", "Avançado", 60, False))
        self.assertEqual(curso.instrutor_id, outro.pk)
        self.assertEqual(resp.data["instrutor_nome"], "Carla")

    def test_delete_de_curso_remove_modulos_e_inscricoes(self):
        Modulo.objects.create(curso=self.curso, titulo="M1", ordem=1)
        Inscricao.objects.create(aluno=self.aluno, curso=self.curso)
        resp = self.client.delete(f"/api/cursos/{self.curso.pk}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Curso.objects.filter(pk=self.curso.pk).exists())
        self.assertFalse(Modulo.objects.filter(curso_id=self.curso.pk).exists())
        self.assertFalse(Inscricao.objects.filter(curso_id=self.curso.pk).exists())


class ModuloApiTests(BaseTestCase):
    def setUp(self):
        self.autenticar_staff()

    def test_crud_modulo_e_filtro_por_curso(self):
        criado = self.client.post("/api/modulos/", {
            "curso": self.curso.pk, "titulo": "SQL", "ordem": 1})
        self.assertEqual(criado.status_code, 201)
        pk = criado.data["id"]
        self.assertTrue(Modulo.objects.filter(pk=pk, curso=self.curso).exists())

        do_outro_curso = self.client.post("/api/modulos/", {
            "curso": self.inativo.pk, "titulo": "Flash", "ordem": 1})
        self.assertEqual(do_outro_curso.status_code, 201)

        # filterset_fields = ["curso"]
        filtrados = self.client.get("/api/modulos/", {"curso": self.curso.pk})
        self.assertEqual([m["id"] for m in filtrados.data], [pk])

        detalhe = self.client.get(f"/api/modulos/{pk}/")
        self.assertEqual(detalhe.status_code, 200)
        self.assertEqual(detalhe.data["titulo"], "SQL")

        atualizado = self.client.patch(f"/api/modulos/{pk}/", {"titulo": "SQL Avançado", "ordem": 2})
        self.assertEqual(atualizado.status_code, 200)
        modulo = Modulo.objects.get(pk=pk)
        self.assertEqual((modulo.titulo, modulo.ordem), ("SQL Avançado", 2))

        excluido = self.client.delete(f"/api/modulos/{pk}/")
        self.assertEqual(excluido.status_code, 204)
        self.assertFalse(Modulo.objects.filter(pk=pk).exists())

    def test_ordem_duplicada_no_mesmo_curso_retorna_400(self):
        Modulo.objects.create(curso=self.curso, titulo="M1", ordem=1)
        resp = self.client.post("/api/modulos/", {
            "curso": self.curso.pk, "titulo": "M1 repetido", "ordem": 1})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Modulo.objects.filter(curso=self.curso, ordem=1).count(), 1)


class InscricaoApiTests(BaseTestCase):
    def setUp(self):
        self.autenticar_staff()
        self.inscricao_ativa = Inscricao.objects.create(aluno=self.aluno, curso=self.curso)
        self.inscricao_inativa = Inscricao.objects.create(aluno=self.aluno, curso=self.inativo)

    def test_lista_detalhe_filtros_e_exclusao(self):
        lista = self.client.get("/api/inscricoes/")
        self.assertEqual(lista.status_code, 200)
        self.assertEqual({i["id"] for i in lista.data},
                         {self.inscricao_ativa.pk, self.inscricao_inativa.pk})

        # filterset_fields = ["aluno", "curso", "concluido"]
        por_aluno = self.client.get("/api/inscricoes/", {"aluno": self.aluno.pk})
        self.assertEqual(len(por_aluno.data), 2)

        por_curso = self.client.get("/api/inscricoes/", {"curso": self.curso.pk})
        self.assertEqual([i["id"] for i in por_curso.data], [self.inscricao_ativa.pk])

        nao_concluidas = self.client.get("/api/inscricoes/", {"concluido": "false"})
        self.assertEqual(len(nao_concluidas.data), 2)

        self.inscricao_ativa.concluido = True
        self.inscricao_ativa.save()
        concluidas = self.client.get("/api/inscricoes/", {"concluido": "true"})
        self.assertEqual([i["id"] for i in concluidas.data], [self.inscricao_ativa.pk])

        detalhe = self.client.get(f"/api/inscricoes/{self.inscricao_ativa.pk}/")
        self.assertEqual(detalhe.status_code, 200)
        self.assertEqual(detalhe.data["aluno_nome"], "Luis")
        self.assertEqual(detalhe.data["curso_titulo"], self.curso.titulo)

        excluido = self.client.delete(f"/api/inscricoes/{self.inscricao_inativa.pk}/")
        self.assertEqual(excluido.status_code, 204)
        self.assertFalse(Inscricao.objects.filter(pk=self.inscricao_inativa.pk).exists())

    def test_desmarcar_conclusao_limpa_data_conclusao(self):
        self.inscricao_ativa.concluido = True
        self.inscricao_ativa.save()
        self.assertIsNotNone(Inscricao.objects.get(pk=self.inscricao_ativa.pk).data_conclusao)

        resp = self.client.patch(f"/api/inscricoes/{self.inscricao_ativa.pk}/", {"concluido": False})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["data_conclusao"])
        self.assertIsNone(Inscricao.objects.get(pk=self.inscricao_ativa.pk).data_conclusao)


class PermissoesApiTests(BaseTestCase):
    def test_leitura_de_inscricoes_exige_login(self):
        self.assertEqual(self.client.get("/api/inscricoes/").status_code, 401)

    def test_escrita_sem_token_nos_recursos(self):
        self.assertEqual(self.client.post("/api/alunos/", {
            "nome": "Bia", "email": "bia@x.com",
            "username": "bia", "password": "senha12345"}).status_code, 401)
        self.assertEqual(self.client.post("/api/instrutores/", {
            "nome": "Bruno", "email": "bruno@x.com"}).status_code, 401)
        self.assertEqual(self.client.post("/api/modulos/", {
            "curso": self.curso.pk, "titulo": "M1", "ordem": 1}).status_code, 401)
        self.assertEqual(self.client.post("/api/inscricoes/", {
            "aluno": self.aluno.pk, "curso": self.curso.pk}).status_code, 401)

        self.assertFalse(Instrutor.objects.filter(email="bruno@x.com").exists())
        self.assertFalse(Modulo.objects.filter(curso=self.curso).exists())
        self.assertFalse(Inscricao.objects.filter(curso=self.curso).exists())


class InscreverActionTests(BaseTestCase):
    def test_usuario_sem_perfil_aluno_recebe_403(self):
        User.objects.create_user("semperfil", "semperfil@x.com", "senha12345")
        login = self.client.post("/api/auth/login/", {"username": "semperfil", "password": "senha12345"})
        self.assertEqual(login.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        resp = self.client.post(f"/api/cursos/{self.curso.pk}/inscrever/")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Inscricao.objects.filter(curso=self.curso).exists())

    def test_inscricao_duplicada_pela_acao_recebe_400(self):
        self.autenticar()
        primeira = self.client.post(f"/api/cursos/{self.curso.pk}/inscrever/")
        self.assertEqual(primeira.status_code, 201)
        segunda = self.client.post(f"/api/cursos/{self.curso.pk}/inscrever/")
        self.assertEqual(segunda.status_code, 400)
        self.assertEqual(Inscricao.objects.filter(aluno=self.aluno, curso=self.curso).count(), 1)

    def test_staff_sem_perfil_aluno_recebe_403(self):
        self.autenticar_staff()
        resp = self.client.post(f"/api/cursos/{self.curso.pk}/inscrever/")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Inscricao.objects.filter(curso=self.curso).exists())


class VisitanteTests(BaseTestCase):
    def test_visitante_nao_acessa_dados_de_alunos(self):
        self.assertEqual(self.client.get("/api/alunos/").status_code, 401)
        self.assertEqual(self.client.get(f"/api/alunos/{self.aluno.pk}/").status_code, 401)

    def test_get_queryset_de_aluno_sem_usuario_autenticado_nao_quebra(self):
        view = AlunoViewSet()
        request = APIRequestFactory().get("/api/alunos/")
        request.user = AnonymousUser()
        view.request = request

        queryset = view.get_queryset()

        self.assertEqual(queryset.count(), 0)
        self.assertFalse(queryset.exists())


class AlunoPerfilProprioTests(BaseTestCase):
    def setUp(self):
        self.autenticar()

    def test_aluno_acessa_e_edita_o_proprio_perfil(self):
        detalhe = self.client.get(f"/api/alunos/{self.aluno.pk}/")
        self.assertEqual(detalhe.status_code, 200)
        self.assertEqual(detalhe.data["email"], "luis@x.com")

        patch = self.client.patch(f"/api/alunos/{self.aluno.pk}/", {"nome": "Luis Editado"})
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(Aluno.objects.get(pk=self.aluno.pk).nome, "Luis Editado")

        put = self.client.put(f"/api/alunos/{self.aluno.pk}/", {"nome": "Luis Put", "email": "luis@x.com"})
        self.assertEqual(put.status_code, 200)
        self.assertEqual(Aluno.objects.get(pk=self.aluno.pk).nome, "Luis Put")

    def test_aluno_troca_a_propria_senha(self):
        resp = self.client.patch(f"/api/alunos/{self.aluno.pk}/", {"password": "novasenha123"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password("novasenha123"))
        login = self.client.post("/api/auth/login/", {"username": "luis", "password": "novasenha123"})
        self.assertEqual(login.status_code, 200)

    def test_aluno_nao_lista_cria_nem_exclui_alunos(self):
        self.assertEqual(self.client.get("/api/alunos/").status_code, 403)
        self.assertEqual(self.client.post("/api/alunos/", {
            "nome": "Novo", "email": "novo@x.com",
            "username": "novo", "password": "senha12345"}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/alunos/{self.aluno.pk}/").status_code, 403)

        self.assertTrue(Aluno.objects.filter(pk=self.aluno.pk).exists())
        self.assertFalse(User.objects.filter(username="novo").exists())
        self.assertEqual(Aluno.objects.count(), 1)

    def test_aluno_nao_acessa_nem_edita_outro_perfil(self):
        outro_user = User.objects.create_user("outro", "outro@x.com", "senha12345")
        outro = Aluno.objects.create(user=outro_user, nome="Outro", email="outro@x.com")

        self.assertEqual(self.client.get(f"/api/alunos/{outro.pk}/").status_code, 404)
        resp = self.client.patch(f"/api/alunos/{outro.pk}/", {
            "nome": "Invadido", "email": "invadido@x.com", "password": "senha99999"})
        self.assertEqual(resp.status_code, 404)
        self.assertNotIn("password", resp.data)

        outro.refresh_from_db()
        outro_user.refresh_from_db()
        self.assertEqual((outro.nome, outro.email), ("Outro", "outro@x.com"))
        self.assertTrue(outro_user.check_password("senha12345"))
        self.assertFalse(outro_user.check_password("senha99999"))

    def test_aluno_nao_altera_vinculo_nem_privilegios(self):
        outro_user = User.objects.create_user("outro2", "outro2@x.com", "senha12345")
        resp = self.client.patch(f"/api/alunos/{self.aluno.pk}/", {
            "user": outro_user.pk, "is_staff": True, "is_superuser": True})
        self.assertEqual(resp.status_code, 200)

        self.aluno.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.aluno.user_id, self.user.pk)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)


class CatalogoPermissoesTests(BaseTestCase):
    def test_visitante_le_o_catalogo(self):
        self.assertEqual(self.client.get("/api/instrutores/").status_code, 200)
        self.assertEqual(self.client.get("/api/cursos/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/cursos/{self.curso.pk}/modulos/").status_code, 200)
        self.assertEqual(self.client.get("/api/modulos/").status_code, 200)

    def test_aluno_nao_escreve_no_catalogo(self):
        self.autenticar()
        modulo = Modulo.objects.create(curso=self.curso, titulo="M1", ordem=1)

        with self.subTest(rota="instrutor"):
            self.assertEqual(self.client.post("/api/instrutores/", {
                "nome": "X", "email": "x@x.com"}).status_code, 403)
            self.assertEqual(self.client.patch(f"/api/instrutores/{self.instrutor.pk}/", {
                "nome": "X"}).status_code, 403)
            self.assertEqual(self.client.delete(f"/api/instrutores/{self.instrutor.pk}/").status_code, 403)

        with self.subTest(rota="curso"):
            self.assertEqual(self.client.post("/api/cursos/", {
                "titulo": "X", "descricao": "d", "carga_horaria": 1,
                "instrutor": self.instrutor.pk}).status_code, 403)
            self.assertEqual(self.client.patch(f"/api/cursos/{self.curso.pk}/", {"titulo": "X"}).status_code, 403)
            self.assertEqual(self.client.delete(f"/api/cursos/{self.curso.pk}/").status_code, 403)

        with self.subTest(rota="modulo"):
            self.assertEqual(self.client.post("/api/modulos/", {
                "curso": self.curso.pk, "titulo": "X", "ordem": 2}).status_code, 403)
            self.assertEqual(self.client.patch(f"/api/modulos/{modulo.pk}/", {"titulo": "X"}).status_code, 403)
            self.assertEqual(self.client.delete(f"/api/modulos/{modulo.pk}/").status_code, 403)

        self.instrutor.refresh_from_db()
        self.curso.refresh_from_db()
        modulo.refresh_from_db()
        self.assertEqual(self.instrutor.nome, "Ana")
        self.assertEqual(self.curso.titulo, "Introdução a Bancos de Dados")
        self.assertEqual(modulo.titulo, "M1")
        self.assertEqual(Instrutor.objects.count(), 1)
        self.assertEqual(Curso.objects.count(), 2)
        self.assertEqual(Modulo.objects.count(), 1)


class InscricaoAlunoTests(BaseTestCase):
    def setUp(self):
        self.autenticar()
        self.outro_user = User.objects.create_user("outro", "outro@x.com", "senha12345")
        self.outro = Aluno.objects.create(user=self.outro_user, nome="Outro", email="outro@x.com")
        self.propria = Inscricao.objects.create(aluno=self.aluno, curso=self.curso)
        self.de_terceiro = Inscricao.objects.create(aluno=self.outro, curso=self.curso)

    def test_aluno_lista_e_detalha_apenas_as_proprias(self):
        lista = self.client.get("/api/inscricoes/")
        self.assertEqual(lista.status_code, 200)
        self.assertEqual([i["id"] for i in lista.data], [self.propria.pk])

        filtrada = self.client.get("/api/inscricoes/", {"aluno": self.outro.pk})
        self.assertEqual(filtrada.data, [])

        self.assertEqual(self.client.get(f"/api/inscricoes/{self.propria.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/inscricoes/{self.de_terceiro.pk}/").status_code, 404)

    def test_aluno_nao_cria_altera_nem_exclui_inscricao_pelo_crud(self):
        self.assertEqual(self.client.post("/api/inscricoes/", {
            "aluno": self.aluno.pk, "curso": self.inativo.pk}).status_code, 403)
        self.assertEqual(self.client.post("/api/inscricoes/", {
            "aluno": self.outro.pk, "curso": self.inativo.pk}).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/inscricoes/{self.propria.pk}/", {
            "concluido": True}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/inscricoes/{self.propria.pk}/").status_code, 403)

        self.assertEqual(Inscricao.objects.count(), 2)
        self.propria.refresh_from_db()
        self.assertFalse(self.propria.concluido)
        self.assertIsNone(self.propria.data_conclusao)
        self.assertFalse(Inscricao.objects.filter(aluno=self.aluno, curso=self.inativo).exists())

    def test_aluno_nao_marca_a_propria_conclusao(self):
        resp = self.client.patch(f"/api/inscricoes/{self.propria.pk}/", {"concluido": True})
        self.assertEqual(resp.status_code, 403)
        self.propria.refresh_from_db()
        self.assertFalse(self.propria.concluido)
        self.assertIsNone(self.propria.data_conclusao)

    def test_usuario_sem_perfil_aluno_nao_lista_inscricoes(self):
        User.objects.create_user("semperfil", "sp@x.com", "senha12345")
        login = self.client.post("/api/auth/login/", {"username": "semperfil", "password": "senha12345"})
        self.assertEqual(login.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        self.assertEqual(self.client.get("/api/inscricoes/").status_code, 403)
        self.assertEqual(Inscricao.objects.count(), 2)


class RelatoriosPermissoesTests(BaseTestCase):
    def test_aluno_nao_acessa_relatorios(self):
        self.autenticar()
        for url in [
            "/api/relatorios/inscricoes-cursos-ativos/",
            "/api/relatorios/cursos-concluintes/",
            "/api/relatorios/carga-horaria-instrutor/",
            "/api/relatorios/alunos-multiplos-cursos/",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
