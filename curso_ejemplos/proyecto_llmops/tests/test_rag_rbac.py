"""
test_rag.py · Clasificación de confidencialidad y recuperación con RBAC
=======================================================================
Todo offline: `clasificar_confidencialidad`, `trocear_con_metadata` y
`filtrar_por_rol` son funciones PURAS. Ni API, ni Postgres, ni embeddings.

Lo único que roza el mundo real (`construir_retriever_*`) no se testea aquí:
se inyecta un RetrieverFalso, que es justo el motivo de que se inyecte.
"""
import pytest

from app import rag

pytestmark = pytest.mark.offline


class TestClasificarConfidencialidad:
    """La heurística que decide qué es secreto.

    Regresión histórica: la primera versión marcaba 'restricted' cualquier texto
    con la palabra 'cifrado' o 'personal'. Como TODA la normativa habla de eso,
    un 'analyst' (el rol por defecto) no recuperaba ni un fragmento. Un
    clasificador que lo marca todo como secreto no protege nada: rompe el
    producto. Estos tests fijan ese comportamiento para que no vuelva.
    """

    def test_marca_restringido_solo_con_marca_explicita(self):
        assert rag.clasificar_confidencialidad("Documento CONFIDENCIAL") == "restricted"
        assert rag.clasificar_confidencialidad("no divulgar fuera del área") == "restricted"
        assert rag.clasificar_confidencialidad("Las claves maestras y el HSM") == "restricted"

    def test_una_regla_normal_es_interna_no_restringida(self):
        # Habla de cifrado y de datos personales: antes esto era 'restricted'.
        regla = ("Regla 1 — Cifrado en reposo: los datos personales de clientes "
                 "deben almacenarse cifrados usando AES-256.")
        assert rag.clasificar_confidencialidad(regla) == "internal"

    def test_lo_publico_debe_declararse(self):
        assert rag.clasificar_confidencialidad("Contactos [público]") == "public"

    def test_por_defecto_interno_no_publico(self):
        # Ante la duda, un documento normativo no se publica.
        assert rag.clasificar_confidencialidad("Un párrafo cualquiera.") == "internal"

    def test_es_pura(self):
        texto = "Regla 3 — Completitud del RUC."
        assert rag.clasificar_confidencialidad(texto) == rag.clasificar_confidencialidad(texto)


class TestTrocearConMetadata:
    def test_cada_fragmento_lleva_su_nivel(self):
        texto = "Primer párrafo normal.\n\nSegundo párrafo CONFIDENCIAL."
        docs = rag.trocear_con_metadata(texto)
        assert [d.metadata["confidentiality"] for d in docs] == ["internal", "restricted"]

    def test_ignora_parrafos_vacios(self):
        assert len(rag.trocear_con_metadata("uno\n\n\n\n   \n\ndos")) == 2


class TestRecuperarConRBAC:
    """El corazón del control de acceso: recuperar primero, autorizar después."""

    def test_el_analyst_no_ve_lo_restringido(self, retriever_falso):
        contexto = rag.recuperar(retriever_falso, "claves", rol="analyst")
        assert "HSM" not in contexto
        assert "Cifrado en reposo" in contexto      # lo público/interno sí

    def test_el_compliance_lo_ve_todo(self, retriever_falso):
        contexto = rag.recuperar(retriever_falso, "claves", rol="compliance")
        assert "HSM" in contexto

    def test_el_rol_publico_solo_ve_lo_publico(self, retriever_falso):
        contexto = rag.recuperar(retriever_falso, "lo que sea", rol="public")
        assert "AES-256" in contexto                # el fragmento 'public'
        assert "auditoría" not in contexto          # el 'internal'
        assert "HSM" not in contexto                # el 'restricted'

    def test_el_retriever_recibe_la_pregunta_entera(self, retriever_falso):
        rag.recuperar(retriever_falso, "¿cómo se cifran los datos?", rol="analyst")
        assert retriever_falso.preguntas == ["¿cómo se cifran los datos?"]

    def test_un_rol_desconocido_cae_al_minimo_privilegio(self, retriever_falso):
        # Un typo en el rol NO debe abrir la puerta: cae a 'public'.
        contexto = rag.recuperar(retriever_falso, "claves", rol="complianze")
        assert "HSM" not in contexto
