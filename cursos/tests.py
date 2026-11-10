from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Aluno, Curso, Inscricao, Instrutor, Modulo


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

    def autenticar(self):
        resp = self.client.post("/api/auth/login/", {"username": "luis", "password": "senha12345"})
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
        self.assertEqual(self.client.post("/api/cursos/", payload).status_code, 201)

    def test_relatorios_exigem_login(self):
        self.assertEqual(self.client.get("/api/relatorios/alunos-multiplos-cursos/").status_code, 401)


class CrudTests(BaseTestCase):
    def setUp(self):
        self.autenticar()

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
        self.autenticar()

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
        self.autenticar()
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
