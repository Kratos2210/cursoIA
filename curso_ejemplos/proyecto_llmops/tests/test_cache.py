"""
test_cache.py · El caché semántico: aciertos, fallos y el agujero de seguridad
==============================================================================
Sin Redis, sin embeddings reales y sin cuota: `EmbeddingsFalsos` devuelve
vectores deterministas de 3 dimensiones (ver conftest.py).

Dos familias de tests, y la segunda importa más que la primera:
  - que el caché ACIERTE cuando debe y FALLE cuando debe,
  - que **no se salte el RBAC**. Un caché compartido entre roles convierte toda
    la gobernanza en decoración.
"""
import pytest

from cache import cache_backends, semantic_cache
from cache.cache_backends import EntradaCache, InMemoryCache
from cache.semantic_cache import SemanticCache

pytestmark = pytest.mark.offline


@pytest.fixture
def cache(embeddings_falsos):
    """Umbral 0.92, el mismo que el .env.example."""
    return SemanticCache(embeddings_falsos, InMemoryCache(), umbral=0.92)


# ==================================================================
# COSENO
# ==================================================================
class TestCoseno:
    def test_vectores_identicos_dan_uno(self):
        assert semantic_cache.coseno([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_vectores_ortogonales_dan_cero(self):
        assert semantic_cache.coseno([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)

    def test_mide_el_angulo_no_la_magnitud(self):
        # ⭐ El mismo tema, un texto el doble de largo: misma dirección.
        assert semantic_cache.coseno([1, 1, 0], [2, 2, 0]) == pytest.approx(1.0)

    def test_un_vector_nulo_no_se_parece_a_nada(self):
        # Sin dirección no hay ángulo. Devolver 0.0 en vez de dividir por cero.
        assert semantic_cache.coseno([0, 0, 0], [1, 2, 3]) == 0.0

    def test_dimensiones_distintas_es_un_error(self):
        with pytest.raises(ValueError, match="dimensión"):
            semantic_cache.coseno([1, 0], [1, 0, 0])


# ==================================================================
# HIT / MISS
# ==================================================================
class TestAciertosYFallos:
    def test_la_pregunta_exacta_acierta(self, cache):
        cache.guardar("¿Hay que cifrar los datos?", "Sí, AES-256.")
        acierto = cache.buscar("¿Hay que cifrar los datos?")
        assert acierto is not None
        assert acierto.respuesta == "Sí, AES-256."

    def test_una_pregunta_REFORMULADA_tambien_acierta(self, cache):
        # ⭐ Lo que un dict no puede hacer: los vectores de las dos preguntas
        #    apuntan casi en la misma dirección (coseno ≈ 0.99).
        cache.guardar("¿Hay que cifrar los datos?", "Sí, AES-256.")
        acierto = cache.buscar("¿Los datos se cifran?")
        assert acierto is not None
        assert acierto.pregunta_original == "¿Hay que cifrar los datos?"
        assert acierto.similitud > 0.92

    def test_una_pregunta_distinta_falla(self, cache):
        cache.guardar("¿Hay que cifrar los datos?", "Sí, AES-256.")
        assert cache.buscar("¿Cuál es el horario de la oficina?") is None

    def test_el_cache_vacio_siempre_falla(self, cache):
        assert cache.buscar("¿Hay que cifrar los datos?") is None

    def test_un_umbral_alto_convierte_el_acierto_en_fallo(self, embeddings_falsos):
        # ⭐ El umbral ES la política. Con 0.999, dos preguntas equivalentes ya
        #    no lo son. Ante la duda, un MISS caro > un HIT equivocado.
        estricto = SemanticCache(embeddings_falsos, InMemoryCache(), umbral=0.999)
        estricto.guardar("¿Hay que cifrar los datos?", "Sí.")
        assert estricto.buscar("¿Los datos se cifran?") is None

    def test_una_pregunta_desconocida_para_los_embeddings_no_acierta(self, cache):
        # Vector nulo → coseno 0 con todo. Un texto que no se supo representar
        # no debe "parecerse" a nada.
        cache.guardar("¿Hay que cifrar los datos?", "Sí.")
        assert cache.buscar("texto que no está en la tabla") is None


class TestMetricasDelCache:
    def test_cuenta_aciertos_y_fallos(self, cache):
        cache.guardar("¿Hay que cifrar los datos?", "Sí.")
        cache.buscar("¿Hay que cifrar los datos?")            # hit
        cache.buscar("¿Cuál es el horario de la oficina?")    # miss
        assert (cache.aciertos, cache.fallos) == (1, 1)
        assert cache.tasa_aciertos == pytest.approx(0.5)

    def test_sin_busquedas_la_tasa_es_cero_y_no_divide_por_cero(self, cache):
        assert cache.tasa_aciertos == 0.0


# ==================================================================
# ⚠️ EL CACHÉ COMO CANAL LATERAL DEL RBAC
# ==================================================================
class TestAislamientoPorRol:
    """El test que justifica que `rol` esté en la clave del caché.

    Sin esto, la optimización de coste se convierte en una fuga de datos: el
    RBAC filtra el retriever, pero el caché devuelve la respuesta ya cocinada
    sin pasar por él.
    """

    def test_un_analyst_NO_recibe_lo_cacheado_para_compliance(self, cache):
        cache.guardar("¿Hay que cifrar los datos?", "Las claves están en el HSM.",
                      rol="compliance")
        # Misma pregunta, misma similitud… otro rol.
        assert cache.buscar("¿Hay que cifrar los datos?", rol="analyst") is None

    def test_compliance_si_recibe_lo_suyo(self, cache):
        cache.guardar("¿Hay que cifrar los datos?", "Las claves están en el HSM.",
                      rol="compliance")
        acierto = cache.buscar("¿Hay que cifrar los datos?", rol="compliance")
        assert acierto is not None and "HSM" in acierto.respuesta

    def test_cada_rol_cachea_su_propia_respuesta(self, cache):
        cache.guardar("¿Hay que cifrar los datos?", "Respuesta pública.", rol="analyst")
        cache.guardar("¿Hay que cifrar los datos?", "Respuesta completa.", rol="compliance")
        assert cache.buscar("¿Hay que cifrar los datos?", rol="analyst").respuesta == "Respuesta pública."
        assert cache.buscar("¿Hay que cifrar los datos?", rol="compliance").respuesta == "Respuesta completa."


# ==================================================================
# BACKENDS
# ==================================================================
class TestInMemoryCache:
    def test_filtra_por_rol_en_el_propio_backend(self):
        # El filtro vive abajo del todo: ninguna capa de arriba puede olvidarlo.
        backend = InMemoryCache()
        backend.guardar(EntradaCache("p", "r", (1.0,), rol="compliance"))
        assert list(backend.entradas("analyst")) == []
        assert len(list(backend.entradas("compliance"))) == 1

    def test_tiene_tope_de_tamaño(self):
        # Un caché sin tope es una fuga de memoria con buena prensa.
        backend = InMemoryCache(maximo=2)
        for i in range(5):
            backend.guardar(EntradaCache(f"p{i}", "r", (1.0,)))
        entradas = list(backend.entradas("analyst"))
        assert len(entradas) == 2
        assert [e.pregunta for e in entradas] == ["p3", "p4"]   # FIFO: se van las viejas

    def test_limpiar_lo_vacia(self):
        backend = InMemoryCache()
        backend.guardar(EntradaCache("p", "r", (1.0,)))
        backend.limpiar()
        assert list(backend.entradas("analyst")) == []


class TestSerializacionParaRedis:
    """Redis solo guarda texto: la entrada tiene que saber ir y volver de JSON."""

    def test_ida_y_vuelta_conserva_todo(self):
        original = EntradaCache("pregunta", "respuesta", (0.1, 0.2), rol="compliance")
        vuelta = EntradaCache.de_json(original.a_json())
        assert vuelta == original

    def test_el_vector_vuelve_como_tupla(self):
        # JSON no distingue lista de tupla; si volviera como lista, `coseno`
        # funcionaría pero `EntradaCache` dejaría de ser hashable/comparable.
        vuelta = EntradaCache.de_json(EntradaCache("p", "r", (0.1, 0.2)).a_json())
        assert isinstance(vuelta.vector, tuple)

    def test_una_entrada_antigua_sin_rol_cae_al_default(self):
        crudo = '{"pregunta": "p", "respuesta": "r", "vector": [1.0]}'
        assert EntradaCache.de_json(crudo).rol == "analyst"


class TestRedisCacheConDoble:
    """RedisCache sin Redis: le inyectamos un cliente falso."""

    class ClienteFalso:
        def __init__(self):
            self.listas: dict[str, list[str]] = {}
            self.expiraciones: dict[str, int] = {}

        def rpush(self, clave, valor):
            self.listas.setdefault(clave, []).append(valor)

        def lrange(self, clave, inicio, fin):
            return self.listas.get(clave, [])

        def expire(self, clave, segundos):
            self.expiraciones[clave] = segundos

    def test_cada_rol_va_a_su_propia_clave(self):
        # El aislamiento del RBAC, hecho de infraestructura y no de un `if`.
        cliente = self.ClienteFalso()
        backend = cache_backends.RedisCache(cliente=cliente)
        backend.guardar(EntradaCache("p", "r", (1.0,), rol="compliance"))
        assert "gobdata:cache:compliance" in cliente.listas
        assert list(backend.entradas("analyst")) == []

    def test_cada_escritura_renueva_el_ttl(self):
        # ⭐ Sin TTL, una respuesta cacheada sobrevive a la normativa que la
        #    justificaba: obsoleta y servida con total confianza.
        cliente = self.ClienteFalso()
        backend = cache_backends.RedisCache(cliente=cliente, ttl_segundos=60)
        backend.guardar(EntradaCache("p", "r", (1.0,)))
        assert cliente.expiraciones["gobdata:cache:analyst"] == 60
