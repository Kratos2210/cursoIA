"""
test_indexado_rbac_sql.py · Ids idempotentes y el RBAC empujado al WHERE
========================================================================
Dos mejoras que la auditoría marcó como ▲ estructurales:

  1) `add_documents(ids=None)` insertaba otra copia en cada reindexado, así que
     el retriever devolvía el mismo párrafo varias veces.
  2) El RBAC se aplicaba en Python: los documentos restringidos SALÍAN de la
     base de datos y se descartaban ya dentro del proceso.

⚠️ ALCANCE HONESTO DE ESTE ARCHIVO: aquí se prueba la lógica PURA —que el id sea
   estable y discriminante, y que el filtro tenga la forma que espera
   langchain-postgres—. Que el upsert no duplique y que el WHERE filtre de
   verdad son afirmaciones sobre POSTGRES, y solo se demuestran contra una base
   real. Esa verificación está pendiente (ver el informe de auditoría).
"""
import pytest
from langchain_core.documents import Document

from app.rag import id_de_fragmento
from guardrails.rbac import JERARQUIA_ROL, filtro_sql, niveles_permitidos

pytestmark = pytest.mark.offline


def doc(texto: str, nivel: str | None = None) -> Document:
    meta = {"confidentiality": nivel} if nivel else {}
    return Document(page_content=texto, metadata=meta)


class TestIdDeFragmento:
    def test_el_mismo_fragmento_da_el_mismo_id(self):
        # La propiedad que hace idempotente el indexado: reindexar la misma
        # normativa produce los mismos ids, y por tanto actualiza en vez de
        # insertar.
        assert id_de_fragmento(doc("Regla 1", "public")) == \
               id_de_fragmento(doc("Regla 1", "public"))

    def test_textos_distintos_dan_ids_distintos(self):
        assert id_de_fragmento(doc("Regla 1")) != id_de_fragmento(doc("Regla 2"))

    def test_cambiar_la_confidencialidad_cambia_el_id(self):
        """⭐ EL CASO QUE JUSTIFICA METER EL NIVEL EN EL HASH.

        Corregir un fragmento mal clasificado (de 'public' a 'restricted') tiene
        que producir un id nuevo. Si solo se hasheara el texto, la corrección
        chocaría con la fila antigua y podría quedar el contenido marcado como
        público para siempre.
        """
        assert id_de_fragmento(doc("Claves del HSM", "public")) != \
               id_de_fragmento(doc("Claves del HSM", "restricted"))

    def test_un_fragmento_sin_etiqueta_tambien_tiene_id(self):
        assert id_de_fragmento(doc("suelto"))

    def test_el_separador_evita_colisiones_por_concatenacion(self):
        # Sin un separador, ("ab", "c") y ("a", "bc") producirían el mismo
        # material a hashear y colisionarían: dos fragmentos distintos
        # compartiendo id significa que uno PISA al otro al indexar.
        assert id_de_fragmento(doc("c", "ab")) != id_de_fragmento(doc("bc", "a"))

    def test_es_estable_entre_ejecuciones(self):
        # Un valor fijo, escrito a mano: si alguien cambia el algoritmo, este
        # test falla y avisa de que TODO lo ya indexado quedaría huérfano
        # (los ids viejos dejarían de coincidir y se duplicaría en vez de
        # actualizar).
        assert id_de_fragmento(doc("Regla 1", "public")) == \
               "ed0ebca66269731af2d66c6d11a25046"


class TestFiltroSQL:
    def test_tiene_la_forma_que_espera_langchain_postgres(self):
        # `$in` es uno de los operadores soportados (verificado contra
        # langchain_postgres.vectorstores.SPECIAL_CASED_OPERATORS).
        f = filtro_sql("analyst")
        assert list(f) == ["confidentiality"]
        assert list(f["confidentiality"]) == ["$in"]

    def test_pide_exactamente_los_niveles_del_rol(self):
        assert set(filtro_sql("analyst")["confidentiality"]["$in"]) == \
               niveles_permitidos("analyst")

    def test_compliance_puede_ver_lo_restringido(self):
        assert "restricted" in filtro_sql("compliance")["confidentiality"]["$in"]

    def test_analyst_NO_puede_ver_lo_restringido(self):
        assert "restricted" not in filtro_sql("analyst")["confidentiality"]["$in"]

    def test_un_rol_desconocido_cae_al_minimo_privilegio(self):
        # Mismo criterio que `niveles_permitidos`: ante la duda, lo público.
        # Un rol con typo no debe abrir la normativa entera.
        assert filtro_sql("adminnn")["confidentiality"]["$in"] == ["public"]

    @pytest.mark.parametrize("rol", sorted(JERARQUIA_ROL))
    def test_coincide_con_el_filtro_de_python_para_todos_los_roles(self, rol):
        """⭐ LOS DOS FILTROS TIENEN QUE DECIDIR LO MISMO.

        Son defensa en profundidad, no alternativas: si divergieran, el de SQL
        podría dejar pasar algo que el de Python creía bloqueado, o al revés, y
        el comportamiento dependería de qué retriever se construyó.
        """
        assert set(filtro_sql(rol)["confidentiality"]["$in"]) == niveles_permitidos(rol)
