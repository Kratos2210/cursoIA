"""
test_retail_cache.py · Caché semántico y embeddings locales. Sin Redis, sin cuota.
"""
import pytest

from proyecto_retail.app.embeddings import EmbeddingsBolsa
from proyecto_retail.cache.cache_backends import InMemoryCache
from proyecto_retail.cache.semantic_cache import SemanticCache, coseno

pytestmark = pytest.mark.offline


def test_coseno_vector_nulo_es_cero():
    assert coseno([0, 0, 0], [1, 2, 3]) == 0.0


def test_coseno_identicos_es_uno():
    assert coseno([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)


class TestEmbeddingsBolsa:
    def test_mismas_palabras_vector_identico(self):
        emb = EmbeddingsBolsa()
        assert emb.embed_query("aretes dorados") == emb.embed_query("dorados aretes")

    def test_es_determinista_entre_llamadas(self):
        emb = EmbeddingsBolsa()
        assert emb.embed_query("collar plateado") == emb.embed_query("collar plateado")


class TestSemanticCache:
    def test_hit_en_pregunta_reformulada(self):
        """'aretes dorados baratos' acierta con 'aretes dorados económicos'
        cuando comparten vocabulario (umbral bajo, para el mecanismo)."""
        cache = SemanticCache(EmbeddingsBolsa(), InMemoryCache(), umbral=0.5)
        cache.guardar("aretes dorados baratos", "Te recomiendo los de S/19.90")
        acierto = cache.buscar("dame aretes dorados baratos por favor")
        assert acierto is not None and "S/19.90" in acierto.respuesta

    def test_miss_en_pregunta_distinta(self):
        cache = SemanticCache(EmbeddingsBolsa(), InMemoryCache(), umbral=0.92)
        cache.guardar("aretes dorados", "algo")
        assert cache.buscar("una cartera negra grande de cuero") is None

    def test_tasa_de_aciertos_se_contabiliza(self):
        cache = SemanticCache(EmbeddingsBolsa(), InMemoryCache(), umbral=0.5)
        cache.guardar("aretes dorados baratos", "r")
        cache.buscar("aretes dorados baratos")     # hit
        cache.buscar("xyz totalmente distinto")    # miss
        assert cache.tasa_aciertos == pytest.approx(0.5)
