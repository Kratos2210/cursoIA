"""
test_rag.py · Las piezas del RAG que NO necesitan la API
========================================================
De las tres cosas que hace rag.py, dos son código nuestro y se pueden
probar gratis: cómo troceamos la normativa y cómo armamos el contexto.
Solo construir_retriever() llama a Gemini, y por eso no se testea aquí.
"""
import pytest
from langchain_core.documents import Document

import config
import rag

pytestmark = pytest.mark.offline


class TestTrocear:
    def test_un_fragmento_por_regla(self):
        """normativa.txt tiene un título + 5 reglas = 6 fragmentos."""
        fragmentos = rag.trocear(rag.leer_normativa())
        assert len(fragmentos) == 6
        assert all(isinstance(f, Document) for f in fragmentos)

    def test_cada_regla_queda_entera_en_su_fragmento(self):
        """Una regla partida a la mitad daría un contexto incompleto al modelo."""
        fragmentos = rag.trocear(rag.leer_normativa())
        # Saltamos el fragmento 0 (el título del documento).
        for i, esperado in enumerate(["Regla 1", "Regla 2", "Regla 3", "Regla 4", "Regla 5"], start=1):
            assert fragmentos[i].page_content.startswith(esperado)

    def test_la_regla_de_cifrado_menciona_aes(self):
        """El contenido concreto que el agente debe poder citar."""
        fragmentos = rag.trocear(rag.leer_normativa())
        assert "AES-256" in fragmentos[1].page_content

    def test_ignora_parrafos_vacios(self):
        assert [d.page_content for d in rag.trocear("uno\n\n\n\n  \n\ndos")] == ["uno", "dos"]

    def test_texto_vacio_no_produce_fragmentos(self):
        assert rag.trocear("") == []


class TestUnir:
    def test_pega_con_linea_en_blanco(self):
        docs = [Document(page_content="A"), Document(page_content="B")]
        assert rag.unir(docs) == "A\n\nB"

    def test_sin_documentos_da_texto_vacio(self):
        """Si el retriever no encuentra nada, el contexto es "", no un crash."""
        assert rag.unir([]) == ""


class TestContexto:
    def test_devuelve_los_fragmentos_del_retriever_como_texto(self, retriever_falso):
        ctx = rag.contexto(retriever_falso, "¿hay que cifrar los datos?")
        assert "AES-256" in ctx
        assert "log de auditoría" in ctx
        # Dos fragmentos -> separados por una línea en blanco.
        assert ctx.count("\n\n") == 1

    def test_le_pasa_la_pregunta_tal_cual_al_retriever(self, retriever_falso):
        """El contexto se busca con la pregunta del usuario, sin reescribirla."""
        rag.contexto(retriever_falso, "¿hay que cifrar?")
        assert retriever_falso.preguntas == ["¿hay que cifrar?"]


class TestLeerNormativa:
    def test_lee_el_archivo_del_proyecto(self):
        assert "Gobierno de Datos" in rag.leer_normativa()

    def test_la_ruta_por_defecto_existe(self):
        """Si esto falla, el proyecto no arranca: mejor saberlo aquí."""
        assert config.RUTA_NORMATIVA.exists()
