"""
test_ab_feedback.py · El A/B de prompts y el feedback 👍/👎, sin modelo
=======================================================================
Tres cosas que probar, y las tres offline:

  · el bucketing es DETERMINISTA y ~uniforme (si no, el A/B no mide nada),
  · el ColectorFeedback agrega bien 👍/👎 y calcula la tasa por variante,
  · los endpoints /feedback y el evento `fin` de /chat cierran el lazo:
    el thread_id fija la variante y el voto se agrega por variante.

Reutiliza los dobles de conftest.py (AgenteFalso, EmbeddingsFalsos) vía las
fixtures que ya existen: la API entera se levanta sin Gemini, Postgres ni Redis.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import EXPERIMENTO_PROMPT, crear_app
from cache.cache_backends import InMemoryCache
from cache.semantic_cache import SemanticCache
from observability.feedback import ColectorFeedback, Voto
from prompts import experimentos, loader

pytestmark = pytest.mark.offline


# ==================================================================
# 0 · La variante B es un prompt cargable de verdad (A/B entre dos YAML)
# ==================================================================
class TestVarianteBCargable:
    def test_la_variante_B_carga_y_espeja_las_variables_de_A(self):
        # Un A/B solo tiene sentido si las dos variantes son intercambiables:
        # mismas variables, distinta redacción.
        a = loader.cargar("agente_gobdata")
        b = loader.cargar("agente_gobdata_conciso")
        assert b.variables == a.variables == ("rol",)

    def test_la_variante_B_se_renderiza_sin_dejar_nada_sin_sustituir(self):
        b = loader.cargar("agente_gobdata_conciso")
        for rol in ("public", "analyst", "compliance"):
            texto = b.render(rol=rol)
            assert rol in texto
            assert "{{" not in texto
        # Conserva la regla de seguridad clave y la condicional por rol.
        assert "NO especules" in b.render(rol="analyst")
        assert "nota_compliance" in b.render(rol="compliance")
        assert "nota_compliance" not in b.render(rol="analyst")

    def test_las_dos_variantes_del_experimento_existen(self):
        for nombre in EXPERIMENTO_PROMPT.variantes:
            assert loader.cargar(nombre).nombre == nombre


# ==================================================================
# 1 · El bucketing: determinista, uniforme y cerrado a la lista
# ==================================================================
class TestAsignarVariante:
    VARIANTES = ["A", "B"]

    def test_es_determinista(self):
        # ⭐ La misma clave SIEMPRE la misma variante: es lo que hace pegajoso el
        #    A/B. Si alternara, un usuario vería A y B en la misma conversación y
        #    no sabríamos a qué variante atribuir su voto.
        clave = "hilo-42"
        primera = experimentos.asignar_variante(clave, self.VARIANTES)
        for _ in range(50):
            assert experimentos.asignar_variante(clave, self.VARIANTES) == primera

    def test_solo_devuelve_variantes_de_la_lista(self):
        for i in range(200):
            v = experimentos.asignar_variante(f"hilo-{i}", self.VARIANTES)
            assert v in self.VARIANTES

    def test_reparto_aproximadamente_uniforme(self):
        # Sobre muchas claves distintas, sha256 reparte parejo. No exigimos 50/50
        # exacto (sería frágil), sino que ninguna variante se lleve <35% ni >65%.
        conteo = {"A": 0, "B": 0}
        n = 2000
        for i in range(n):
            conteo[experimentos.asignar_variante(f"usuario-{i}", self.VARIANTES)] += 1
        for cantidad in conteo.values():
            assert 0.35 * n < cantidad < 0.65 * n

    def test_tres_variantes_tambien_reparte(self):
        variantes = ["A", "B", "C"]
        vistas = {experimentos.asignar_variante(f"k{i}", variantes) for i in range(200)}
        assert vistas == {"A", "B", "C"}

    def test_lista_vacia_es_error(self):
        with pytest.raises(ValueError):
            experimentos.asignar_variante("x", [])

    def test_no_depende_del_hash_aleatorio_del_proceso(self):
        # Un valor fijado: si alguien cambiara sha256 por hash() de Python (que
        # está aleatorizado por PYTHONHASHSEED), este assert lo delataría.
        assert experimentos.asignar_variante("hilo-42", self.VARIANTES) in self.VARIANTES
        # Y coincide con la clase Experimento, que delega en la misma función.
        exp = experimentos.Experimento("t", ("A", "B"))
        assert exp.variante_de("hilo-42") == experimentos.asignar_variante("hilo-42", self.VARIANTES)


class TestExperimento:
    def test_variante_de_es_pegajosa(self):
        exp = experimentos.Experimento("prompt_conciso", ("A", "B"))
        assert exp.variante_de("hilo-9") == exp.variante_de("hilo-9")

    def test_sin_variantes_es_error(self):
        with pytest.raises(ValueError):
            experimentos.Experimento("vacio", ())


# ==================================================================
# 2 · El colector de feedback: agrega 👍/👎 por variante
# ==================================================================
class TestColectorFeedback:
    def test_cuenta_pulgares_por_variante(self):
        col = ColectorFeedback()
        col.registrar(variante="A", util=True)
        col.registrar(variante="A", util=True)
        col.registrar(variante="A", util=False)
        col.registrar(variante="B", util=False)

        resumen = col.resumen()
        assert resumen["A"] == {"util": 2, "no_util": 1, "total": 3,
                                "tasa_aprobacion": pytest.approx(0.667, abs=0.001)}
        assert resumen["B"]["total"] == 1
        assert resumen["B"]["tasa_aprobacion"] == pytest.approx(0.0)

    def test_la_tasa_es_pulgares_arriba_sobre_total(self):
        col = ColectorFeedback()
        for _ in range(3):
            col.registrar(variante="B", util=True)
        col.registrar(variante="B", util=False)
        assert col.resumen()["B"]["tasa_aprobacion"] == pytest.approx(0.75)

    def test_resumen_vacio(self):
        assert ColectorFeedback().resumen() == {}

    def test_registrar_devuelve_un_voto_inmutable(self):
        voto = ColectorFeedback().registrar(variante="A", util=True, thread_id="h1")
        assert isinstance(voto, Voto)
        with pytest.raises(Exception):
            voto.util = False   # frozen dataclass


# ==================================================================
# 3 · Los endpoints y el evento `fin`, con la API real y dobles
# ==================================================================
@pytest.fixture
def agente(fabrica_agente):
    return fabrica_agente(["Sí, la Regla 1 exige cifrado AES-256 en reposo ",
                           "para todos los datos personales de clientes."])


@pytest.fixture
def cliente(agente, embeddings_falsos):
    cache = SemanticCache(embeddings_falsos, InMemoryCache(), umbral=0.92)
    feedback = ColectorFeedback()
    app = crear_app(agente=agente, cache=cache, feedback=feedback)
    with TestClient(app) as cliente:
        cliente.feedback = feedback
        yield cliente


def _eventos_fin(cuerpo: str) -> list[dict]:
    """Extrae los payloads JSON de los eventos SSE `fin` de un cuerpo de /chat."""
    payloads = []
    lineas = cuerpo.splitlines()
    for i, linea in enumerate(lineas):
        if linea.strip() == "event: fin":
            # el `data:` viene en una línea próxima
            for siguiente in lineas[i + 1:]:
                if siguiente.startswith("data: "):
                    payloads.append(json.loads(siguiente[len("data: "):]))
                    break
    return payloads


class TestEventoFinLlevaVariante:
    def test_el_fin_normal_incluye_variante(self, cliente):
        respuesta = cliente.post("/chat", json={"mensaje": "¿Hay que cifrar los datos?"})
        fines = _eventos_fin(respuesta.text)
        assert fines and "variante" in fines[0]
        assert fines[0]["variante"] in EXPERIMENTO_PROMPT.variantes
        # ⭐ ADITIVO: las claves que fijan los smoke tests siguen ahí.
        assert fines[0]["cache_hit"] is False

    def test_el_fin_de_cache_hit_tambien_incluye_variante(self, cliente):
        pregunta = {"mensaje": "¿Hay que cifrar los datos?"}
        cliente.post("/chat", json=pregunta)
        segunda = cliente.post("/chat", json=pregunta)   # HIT
        fines = _eventos_fin(segunda.text)
        assert fines[0]["cache_hit"] is True
        assert "variante" in fines[0]

    def test_el_mismo_thread_recibe_siempre_la_misma_variante(self, cliente):
        # Distintas preguntas, mismo hilo → misma variante (pegajoso).
        vistas = set()
        for msg in ("¿Hay que cifrar los datos?", "¿Los datos se cifran?"):
            r = cliente.post("/chat", json={"mensaje": msg, "thread_id": "hilo-fijo"})
            vistas |= {f["variante"] for f in _eventos_fin(r.text)}
        assert len(vistas) == 1


class TestEndpointsFeedback:
    def test_post_registra_y_aparece_en_get(self, cliente):
        r = cliente.post("/feedback", json={"thread_id": "h1", "util": True,
                                            "variante": "agente_gobdata"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        resumen = cliente.get("/feedback").json()
        assert resumen["agente_gobdata"]["util"] == 1
        assert resumen["agente_gobdata"]["tasa_aprobacion"] == pytest.approx(1.0)

    def test_un_pulgar_abajo_baja_la_tasa(self, cliente):
        cliente.post("/feedback", json={"util": True, "variante": "B"})
        cliente.post("/feedback", json={"util": False, "variante": "B"})
        assert cliente.get("/feedback").json()["B"]["tasa_aprobacion"] == pytest.approx(0.5)

    def test_sin_variante_se_deriva_del_thread(self, cliente):
        # El cliente no manda variante: el servidor la deriva del thread_id, con
        # la misma asignación pegajosa que anunció en el evento `fin`.
        esperada = EXPERIMENTO_PROMPT.variante_de("hilo-7")
        cliente.post("/feedback", json={"thread_id": "hilo-7", "util": True})
        resumen = cliente.get("/feedback").json()
        assert resumen[esperada]["total"] == 1

    def test_falta_util_lo_rechaza_pydantic(self, cliente):
        # `util` es obligatorio: sin él, 422 antes de tocar nuestro código.
        assert cliente.post("/feedback", json={"thread_id": "h1"}).status_code == 422

    def test_el_voto_no_ensucia_metrics(self, cliente):
        # El feedback vive en su propio endpoint: /metrics no gana claves nuevas.
        cliente.post("/feedback", json={"util": True, "variante": "A"})
        assert "tasa_aprobacion" not in cliente.get("/metrics").json()


# ==================================================================
# 4 · El lazo A/B CERRADO: cada variante usa SU prompt (ADR-0006)
# ==================================================================
class TestElAgenteUsaElPromptDeSuVariante:
    """Antes medíamos solo la infraestructura del A/B (repartir + agregar votos);
    ahora la variante elige el AGENTE, y cada agente estrena el prompt de SU
    variante. Estos tests fijan justo eso: sin ellos, un refactor podría volver a
    servir el prompt por defecto a las dos ramas sin que nadie se entere."""

    def test_prompt_de_variante_carga_el_yaml_de_esa_variante(self):
        from app.agent import prompt_de_variante

        a = prompt_de_variante("agente_gobdata", "analyst")
        b = prompt_de_variante("agente_gobdata_conciso", "analyst")
        # Cada variante rinde SU archivo: son textos distintos, no el mismo.
        assert a != b
        assert b == loader.cargar("agente_gobdata_conciso").render(rol="analyst")

    def test_construir_agentes_hornea_el_prompt_de_cada_variante(self, monkeypatch):
        from app import agent as agent_mod

        # Falseamos las piezas caras (modelo, pgvector) y espiamos el prompt con
        # que se construye cada grafo: es lo único que cambia entre variantes.
        monkeypatch.setattr(agent_mod, "_piezas_caras",
                            lambda usar_pgvector=True: (None, None, None))
        prompts_vistos = {}

        def espia(llm, retriever, evaluador, *, rol="analyst", prompt=None):
            prompts_vistos[prompt] = rol
            return f"agente::{prompt}"

        monkeypatch.setattr(agent_mod, "construir_agente", espia)

        agentes = agent_mod.construir_agentes_por_variante(
            EXPERIMENTO_PROMPT.variantes, rol="analyst")

        # Un agente por variante, cada uno horneado con el prompt de SU archivo.
        assert set(agentes) == set(EXPERIMENTO_PROMPT.variantes)
        for variante in EXPERIMENTO_PROMPT.variantes:
            esperado = agent_mod.prompt_de_variante(variante, "analyst")
            assert agentes[variante] == f"agente::{esperado}"
            assert esperado in prompts_vistos

    def test_el_thread_enruta_al_agente_de_su_variante(self, embeddings_falsos,
                                                       fabrica_agente):
        # Dos agentes distinguibles; se inyecta uno POR variante.
        agente_a = fabrica_agente(["soy A"])
        agente_b = fabrica_agente(["soy B"])
        agentes = {"agente_gobdata": agente_a, "agente_gobdata_conciso": agente_b}
        cache = SemanticCache(embeddings_falsos, InMemoryCache(), umbral=0.92)

        # hilo-2 → variante A ; hilo-0 → variante B (asignación pegajosa por hash).
        assert EXPERIMENTO_PROMPT.variante_de("hilo-2") == "agente_gobdata"
        assert EXPERIMENTO_PROMPT.variante_de("hilo-0") == "agente_gobdata_conciso"

        with TestClient(crear_app(agentes=agentes, cache=cache)) as cliente:
            # Preguntas de coseno 0 entre sí: ningún HIT de caché salta al agente.
            cliente.post("/chat", json={"mensaje": "¿Cuál es el horario de la oficina?",
                                        "thread_id": "hilo-2"})
            cliente.post("/chat", json={"mensaje": "¿Hay que cifrar los datos?",
                                        "thread_id": "hilo-0"})

        def hilos_de(agente):
            return {inv["config"]["configurable"]["thread_id"]
                    for inv in agente.invocaciones}

        # Cada hilo activó SOLO el agente de su variante — no el del otro.
        assert hilos_de(agente_a) == {"hilo-2"}
        assert hilos_de(agente_b) == {"hilo-0"}
