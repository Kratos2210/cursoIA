"""
test_evals.py · La tríada RAG y el gate, sin llamar a ningún juez de verdad
===========================================================================
El juez es un LLM, y un LLM no cabe en un test. Pero `evaluar_puertas` y
`muestrear` son funciones PURAS, y `evaluar_triada` recibe el juez por
parámetro: le pasamos un `JuezFalso` con notas de guion.

⭐ Lo que de verdad se prueba aquí es **el gate**. Un gate sin tests es un gate
   que un día dejó de vetar y nadie se enteró hasta el incidente.
"""
import pytest

from evals import ci_gate, judge, rag_triad, run_evals
from evals.judge import Veredicto
from evals.rag_triad import ResultadoTriada
from evals.run_evals import Ejemplo, Reporte

pytestmark = pytest.mark.offline


class JuezFalso:
    """Se hace pasar por `llm.with_structured_output(Veredicto)`.

    Devuelve las notas del guion, en orden. Guarda los prompts recibidos para
    poder afirmar QUÉ vio cada rúbrica (y, sobre todo, qué NO vio).
    """

    def __init__(self, notas: list[float]):
        self.notas = list(notas)
        self.prompts: list[str] = []

    def invoke(self, prompt, *args, **kwargs) -> Veredicto:
        self.prompts.append(prompt)
        if not self.notas:
            raise AssertionError("El juez recibió más llamadas que notas en el guion.")
        return Veredicto(puntuacion=self.notas.pop(0), justificacion="guion")


def _triada(faith: float, rel: float, prec: float, pregunta: str = "p") -> ResultadoTriada:
    """Un ResultadoTriada a mano, para probar el gate sin juez."""
    return ResultadoTriada(
        pregunta=pregunta,
        faithfulness=Veredicto(puntuacion=faith, justificacion=""),
        answer_relevance=Veredicto(puntuacion=rel, justificacion=""),
        context_precision=Veredicto(puntuacion=prec, justificacion=""),
    )


# ==================================================================
# EL JUEZ
# ==================================================================
class TestVeredicto:
    def test_la_puntuacion_esta_acotada(self):
        # `with_structured_output` haría reintentar al modelo si se sale del rango.
        with pytest.raises(Exception):
            Veredicto(puntuacion=1.5, justificacion="")

    def test_el_preambulo_combate_los_sesgos_conocidos(self):
        # Verbosidad y refugio en el 0.5: los dos sesgos clásicos del juez.
        assert "longitud" in judge.PREAMBULO.lower()
        assert "0.5" in judge.PREAMBULO


# ==================================================================
# LA TRÍADA · cada métrica mira solo DOS vértices
# ==================================================================
class TestIndependenciaDeLasMetricas:
    """Que cada rúbrica ignore un vértice es lo que las hace independientes."""

    def test_faithfulness_no_ve_la_pregunta(self):
        juez = JuezFalso([1.0])
        rag_triad.faithfulness(juez, respuesta="R", contexto="C")
        assert "PREGUNTA" not in juez.prompts[0]

    def test_answer_relevance_no_ve_el_contexto(self):
        juez = JuezFalso([1.0])
        rag_triad.answer_relevance(juez, pregunta="P", respuesta="R")
        assert "CONTEXTO" not in juez.prompts[0]

    def test_context_precision_no_ve_la_respuesta(self):
        juez = JuezFalso([1.0])
        rag_triad.context_precision(juez, pregunta="P", contexto="C")
        assert "RESPUESTA" not in juez.prompts[0]


class TestEvaluarTriada:
    def test_hace_TRES_llamadas_independientes(self):
        # ⭐ Pedir las tres notas en un solo prompt sería más barato y peor: el
        #    juez arrastraría su impresión de una métrica a las otras (halo).
        juez = JuezFalso([1.0, 0.8, 0.6])
        rag_triad.evaluar_triada(juez, "P", "R", "C")
        assert len(juez.prompts) == 3

    def test_el_score_es_la_media(self):
        juez = JuezFalso([1.0, 1.0, 0.4])
        resultado = rag_triad.evaluar_triada(juez, "P", "R", "C")
        assert resultado.score == pytest.approx(0.8)

    def test_la_peor_metrica_es_el_diagnostico(self):
        # Un context_precision bajo señala al RETRIEVER, no al prompt.
        resultado = _triada(faith=1.0, rel=0.9, prec=0.2)
        assert resultado.peor_metrica == ("context_precision", 0.2)

    def test_la_media_esconde_la_alucinacion(self):
        # faithfulness=0.0 (alucinó del todo) pero el score sale 0.67.
        # Este test documenta POR QUÉ el gate necesita una segunda puerta.
        resultado = _triada(faith=0.0, rel=1.0, prec=1.0)
        assert resultado.score == pytest.approx(2 / 3)
        assert resultado.peor_metrica == ("faithfulness", 0.0)


# ==================================================================
# EL DATASET
# ==================================================================
class TestCargarDataset:
    def test_carga_el_dataset_real_del_repo(self):
        ejemplos = run_evals.cargar_dataset()
        assert len(ejemplos) >= 10
        assert all(isinstance(e, Ejemplo) for e in ejemplos)

    def test_el_dataset_cubre_los_casos_que_importan(self):
        # Un dataset solo de preguntas fáciles no detecta ninguna regresión.
        categorias = {e.categoria for e in run_evals.cargar_dataset()}
        assert "trampa_alucinacion" in categorias      # ¿se inventa lo que no está?
        assert "rbac_denegado" in categorias           # ¿respeta el nivel de acceso?
        assert "contexto_ruidoso" in categorias        # ¿aguanta fragmentos de más?

    def test_los_ids_son_unicos(self):
        # El muestreo determinista se apoya en el id: un duplicado lo rompería.
        ids = [e.id for e in run_evals.cargar_dataset()]
        assert len(ids) == len(set(ids))

    def test_una_linea_rota_falla_ruidosamente(self, tmp_path):
        # Saltársela en silencio = evaluar menos casos de los que crees.
        malo = tmp_path / "roto.jsonl"
        malo.write_text('{"id": "a", "pregunta": "p"}\nesto no es json\n', encoding="utf-8")
        with pytest.raises(ValueError, match="línea inválida"):
            run_evals.cargar_dataset(malo)

    def test_ignora_lineas_vacias(self, tmp_path):
        bueno = tmp_path / "ok.jsonl"
        bueno.write_text(
            '{"id":"a","pregunta":"p","respuesta_esperada":"r","contexto":"c"}\n\n',
            encoding="utf-8",
        )
        assert len(run_evals.cargar_dataset(bueno)) == 1


class TestMuestreoDeterminista:
    @pytest.fixture
    def ejemplos(self):
        return [Ejemplo(id=f"e{i}", pregunta="p", respuesta_esperada="r", contexto="c")
                for i in range(10)]

    def test_la_fraccion_completa_devuelve_todo(self, ejemplos):
        assert len(run_evals.muestrear(ejemplos, 1.0)) == 10

    def test_coge_la_fraccion_pedida(self, ejemplos):
        assert len(run_evals.muestrear(ejemplos, 0.3)) == 3

    def test_el_mismo_dataset_da_SIEMPRE_la_misma_muestra(self, ejemplos):
        # ⭐ Un CI que evalúa ejemplos distintos cada vez no mide regresiones:
        #    mide el azar. Y un gate que parpadea se acaba desactivando.
        primera = [e.id for e in run_evals.muestrear(ejemplos, 0.3)]
        segunda = [e.id for e in run_evals.muestrear(ejemplos, 0.3)]
        assert primera == segunda

    def test_nunca_devuelve_cero_ejemplos_con_una_fraccion_positiva(self, ejemplos):
        # 10 × 0.01 = 0.1 → redondearía a 0 y el gate aprobaría un dataset vacío.
        assert len(run_evals.muestrear(ejemplos, 0.01)) == 1

    def test_fraccion_cero_no_evalua_nada(self, ejemplos):
        assert run_evals.muestrear(ejemplos, 0.0) == []


# ==================================================================
# EL REPORTE
# ==================================================================
class TestReporte:
    def test_evaluar_dataset_sin_responder_mide_al_JUEZ(self):
        # Sin `responder`, se juzga la respuesta esperada del dataset. Sirve para
        # calibrar la rúbrica (lo bueno debe sacar ~1.0), no para evaluar el agente.
        juez = JuezFalso([1.0] * 3)
        ejemplos = [Ejemplo("a", "¿p?", "respuesta buena", "contexto")]
        reporte = run_evals.evaluar_dataset(juez, ejemplos)
        assert reporte.score == 1.0

    def test_evaluar_dataset_usa_el_responder_inyectado(self):
        juez = JuezFalso([1.0] * 3)
        llamadas = []

        def responder(pregunta, rol):
            llamadas.append((pregunta, rol))
            return "respuesta del agente", "contexto recuperado"

        ejemplos = [Ejemplo("a", "¿p?", "esperada", "ctx", rol="compliance")]
        run_evals.evaluar_dataset(juez, ejemplos, responder)
        assert llamadas == [("¿p?", "compliance")]

    def test_medias_por_metrica_es_el_diagnostico(self):
        reporte = Reporte([_triada(1.0, 1.0, 0.2), _triada(1.0, 1.0, 0.4)])
        medias = reporte.medias_por_metrica()
        assert medias["context_precision"] == pytest.approx(0.3)
        assert medias["faithfulness"] == 1.0

    def test_el_peor_ejemplo_es_por_donde_se_empieza(self):
        reporte = Reporte([_triada(1, 1, 1, "buena"), _triada(0, 0, 0, "rota")])
        assert reporte.peor.pregunta == "rota"

    def test_un_reporte_vacio_puntua_cero_y_no_revienta(self):
        assert Reporte([]).score == 0.0
        assert Reporte([]).peor is None


# ==================================================================
# ⭐ EL GATE · las dos puertas
# ==================================================================
class TestGate:
    UMBRAL = 0.7

    def test_aprueba_un_sistema_sano(self):
        reporte = Reporte([_triada(1.0, 0.9, 0.9), _triada(0.9, 1.0, 0.8)])
        aprobado, motivos = ci_gate.evaluar_puertas(reporte, self.UMBRAL)
        assert aprobado is True
        assert motivos == []

    def test_la_puerta_de_la_MEDIA_bloquea_la_degradacion_general(self):
        reporte = Reporte([_triada(0.6, 0.6, 0.6), _triada(0.6, 0.6, 0.6)])
        aprobado, motivos = ci_gate.evaluar_puertas(reporte, self.UMBRAL)
        assert aprobado is False
        assert "Degradación general" in motivos[0]

    def test_la_puerta_del_MINIMO_bloquea_el_caso_roto_que_la_media_esconde(self):
        # ⭐ EL TEST QUE JUSTIFICA LA SEGUNDA PUERTA.
        #    20 ejemplos perfectos + 1 catastrófico (el agente reveló las claves
        #    maestras a un analyst). La media sale 0.95 y pasaría la puerta 1.
        reporte = Reporte([_triada(1.0, 1.0, 1.0) for _ in range(20)]
                          + [_triada(0.0, 0.0, 0.0, "¿dónde están las claves?")])
        assert reporte.score > self.UMBRAL          # la media aprueba…

        aprobado, motivos = ci_gate.evaluar_puertas(reporte, self.UMBRAL)
        assert aprobado is False                     # …pero el gate NO.
        assert "Ejemplo crítico" in motivos[0]
        assert "claves" in motivos[0]

    def test_un_bajon_leve_aislado_NO_bloquea(self):
        # 0.6 en un ejemplo es ruido del juez, no un caso roto. El umbral
        # crítico (0.5) es más laxo que el de la media a propósito.
        reporte = Reporte([_triada(1.0, 1.0, 1.0) for _ in range(5)] + [_triada(0.6, 0.6, 0.6)])
        aprobado, _ = ci_gate.evaluar_puertas(reporte, self.UMBRAL)
        assert aprobado is True

    def test_un_dataset_vacio_NO_aprueba(self):
        # "Cero ejemplos evaluados, cero fallos" no es un aprobado: es un bug
        # de configuración que dejaría pasar cualquier deploy.
        aprobado, motivos = ci_gate.evaluar_puertas(Reporte([]), self.UMBRAL)
        assert aprobado is False
        assert "vacío" in motivos[0]

    def test_el_motivo_nombra_la_metrica_que_falla(self):
        reporte = Reporte([_triada(0.0, 1.0, 1.0, "pregunta trampa")])
        _, motivos = ci_gate.evaluar_puertas(reporte, self.UMBRAL)
        assert any("faithfulness" in m for m in motivos)
