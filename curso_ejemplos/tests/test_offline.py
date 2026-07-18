"""
test_offline.py · Tests de los ejemplos, SIN llamar a la API
=============================================================
FINALIDAD:
  Garantizar que los ejemplos del curso siguen funcionando cuando
  actualizas librerías, SIN gastar un solo token de cuota.

  Cada test aquí ejercita la parte NO-LLM de un ejemplo: la aritmética
  de una tool, los moldes Pydantic, las fórmulas de BM25/RRF, el grafo
  de LangGraph, el protocolo MCP… Todo eso es código tuyo y puede
  romperse; el LLM no.

LÓGICA:
  Usamos la fixture 'importar_ejemplo' (de conftest.py) para cargar
  archivos cuyo nombre empieza por número ('07_herramientas.py'), que
  Python no deja importar con un 'import' normal.

  ⚠️ Importar un ejemplo NO ejecuta su main(): todos los ejemplos están
     protegidos con 'if __name__ == "__main__"'. Por eso importarlos es
     seguro y gratis.

Ejecuta:  uv run pytest curso_ejemplos/tests/ -m offline -v
"""
import asyncio
import math
import os
import random
import sys
from collections import Counter

import pytest

# Todos los tests de este archivo son offline (no tocan la API de Gemini).
pytestmark = pytest.mark.offline


# ==================================================================
# TEMA 07 · Herramientas (@tool)
# ==================================================================
class TestTema07Herramientas:
    """La tool es una función normal + metadatos que el modelo LEE."""

    def test_calculo_del_descuento(self, importar_ejemplo):
        """3500 con 18% de descuento -> 2870. Si esto falla, el agente miente."""
        m = importar_ejemplo("07_herramientas")
        assert m.calculadora_descuentos.invoke({"precio": 3500, "porcentaje": 18}) == 2870.0

    def test_descuento_de_cero_no_cambia_el_precio(self, importar_ejemplo):
        m = importar_ejemplo("07_herramientas")
        assert m.calculadora_descuentos.invoke({"precio": 100, "porcentaje": 0}) == 100.0

    def test_descuento_total_deja_el_precio_en_cero(self, importar_ejemplo):
        m = importar_ejemplo("07_herramientas")
        assert m.calculadora_descuentos.invoke({"precio": 100, "porcentaje": 100}) == 0.0

    def test_metadatos_que_ve_el_modelo(self, importar_ejemplo):
        """El nombre, la descripción y los args son el CONTRATO con el modelo.

        Si el docstring desaparece, el modelo deja de saber cuándo usar la
        tool: es un bug silencioso que este test convierte en un fallo ruidoso.
        """
        tool = importar_ejemplo("07_herramientas").calculadora_descuentos
        assert tool.name == "calculadora_descuentos"
        assert "descuento" in tool.description.lower()
        # Los dos parámetros, con su tipo, tal como los lee el modelo:
        assert set(tool.args) == {"precio", "porcentaje"}
        assert tool.args["precio"]["type"] == "number"


# ==================================================================
# TEMA 05 · Salida estructurada (moldes Pydantic)
# ==================================================================
class TestTema05SalidaEstructurada:
    """Los moldes se validan solos: no hace falta el LLM para probarlos."""

    def test_persona_con_edad(self, importar_ejemplo):
        m = importar_ejemplo("05_salida_estructurada")
        p = m.Persona(nombre="Ana", edad=30)
        assert p.nombre == "Ana" and p.edad == 30

    def test_persona_sin_edad_usa_none(self, importar_ejemplo):
        """'edad' es Optional con default=None: se puede omitir."""
        p = importar_ejemplo("05_salida_estructurada").Persona(nombre="Marta")
        assert p.edad is None

    def test_persona_sin_nombre_es_invalida(self, importar_ejemplo):
        """'nombre' es obligatorio: Pydantic debe rechazar el objeto."""
        from pydantic import ValidationError
        m = importar_ejemplo("05_salida_estructurada")
        with pytest.raises(ValidationError):
            m.Persona(edad=30)

    def test_extraccion_es_una_lista_de_personas(self, importar_ejemplo):
        """El molde Extraccion busca a TODAS las personas, no solo una."""
        m = importar_ejemplo("05_salida_estructurada")
        e = m.Extraccion(personas=[{"nombre": "Ana", "edad": 30}, {"nombre": "Luis", "edad": 5}])
        assert len(e.personas) == 2
        assert [p.nombre for p in e.personas] == ["Ana", "Luis"]
        # Pydantic convirtió los diccionarios en objetos Persona de verdad:
        assert isinstance(e.personas[0], m.Persona)

    def test_extraccion_vacia_es_valida(self, importar_ejemplo):
        """Un texto sin personas produce una lista vacía, no un error."""
        assert importar_ejemplo("05_salida_estructurada").Extraccion(personas=[]).personas == []

    def test_etiqueta_de_tagging(self, importar_ejemplo):
        m = importar_ejemplo("05_salida_estructurada")
        et = m.Etiqueta(sentimiento="positivo", idioma="inglés")
        assert et.sentimiento == "positivo"

    def test_los_campos_llevan_description(self, importar_ejemplo):
        """El 'description' de cada Field es lo que guía al modelo al rellenar.

        Sin él, with_structured_output produce basura. Lo blindamos.
        """
        m = importar_ejemplo("05_salida_estructurada")
        for campo in m.Etiqueta.model_fields.values():
            assert campo.description, "todo Field debe describir qué se espera"


# ==================================================================
# TEMA 06 · Runnables de composición
# ==================================================================
class TestTema06Runnables:
    """Los conectores de LCEL funcionan sin ningún modelo detrás."""

    def test_runnable_lambda_mete_una_funcion_en_la_cadena(self):
        from langchain_core.runnables import RunnableLambda
        assert RunnableLambda(lambda x: x.upper()).invoke("hola mundo") == "HOLA MUNDO"

    def test_runnable_passthrough_no_toca_el_dato(self):
        from langchain_core.runnables import RunnablePassthrough
        assert RunnablePassthrough().invoke("importante") == "importante"

    def test_runnable_parallel_devuelve_un_diccionario(self):
        """Es el patrón exacto del RAG: una rama busca, la otra deja pasar."""
        from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
        demo = RunnableParallel(
            original=RunnablePassthrough(),
            gritado=RunnableLambda(lambda x: x.upper()),
        )
        assert demo.invoke("importante") == {"original": "importante", "gritado": "IMPORTANTE"}

    def test_el_operador_tuberia_encadena(self):
        """'|' es composición: la salida de uno entra al siguiente."""
        from langchain_core.runnables import RunnableLambda
        cadena = RunnableLambda(str.strip) | RunnableLambda(str.upper)
        assert cadena.invoke("  hola  ") == "HOLA"


# ==================================================================
# TEMA 11 · RAG — las piezas puras (trocear y unir)
# ==================================================================
class TestTema11Rag:
    """El troceado y el pegado de contexto son código tuyo: se testean."""

    def test_trocear_devuelve_documentos(self, importar_ejemplo, texto_datos_rag):
        from langchain_core.documents import Document
        docs = importar_ejemplo("11_rag").trocear(texto_datos_rag)
        assert len(docs) == 7
        assert all(isinstance(d, Document) for d in docs)
        assert docs[2].page_content.startswith("Horario de atención:")

    def test_trocear_ignora_parrafos_vacios(self, importar_ejemplo):
        docs = importar_ejemplo("11_rag").trocear("uno\n\n\n\n  \n\ndos")
        assert [d.page_content for d in docs] == ["uno", "dos"]

    def test_unir_pega_los_documentos_con_linea_en_blanco(self, importar_ejemplo):
        """El contexto que ve el LLM: fragmentos separados por línea en blanco."""
        from langchain_core.documents import Document
        m = importar_ejemplo("11_rag")
        docs = [Document(page_content="A"), Document(page_content="B")]
        assert m.unir(docs) == "A\n\nB"

    def test_unir_sin_documentos_da_texto_vacio(self, importar_ejemplo):
        """Si el retriever no encuentra nada, el contexto es "" (no revienta)."""
        assert importar_ejemplo("11_rag").unir([]) == ""

    def test_ida_y_vuelta(self, importar_ejemplo, texto_datos_rag):
        """trocear -> unir reconstruye el documento (normalizado)."""
        m = importar_ejemplo("11_rag")
        assert m.unir(m.trocear(texto_datos_rag)) == texto_datos_rag.strip()


# ==================================================================
# TEMA 12 · RAG híbrido: BM25 + coseno + RRF + re-ranking
# ==================================================================
# Los índices de chunk de datos_rag.txt (7 párrafos), para leer los tests:
CHUNK_TITULO = 0        # "Manual de la empresa Datawith.AI"  (ruido)
CHUNK_HORARIO = 2       # "Horario de atención: ..."
CHUNK_ENTREGABLES = 5   # "Entregables de un proyecto: ... capacitación de 2 horas"

PREGUNTA_HORARIO = "¿Cuál es el horario de atención de soporte?"


@pytest.fixture(scope="module")
def m12(importar_ejemplo):
    return importar_ejemplo("12_rag_hibrido_rerank")


class TestTema12Tokenizar:
    def test_pasa_a_minusculas_y_quita_puntuacion(self, m12):
        assert m12.tokenizar("¿Cuál es el HORARIO, de atención?") == [
            "cuál", "es", "el", "horario", "de", "atención"]

    def test_conserva_numeros_y_guiones(self, m12):
        """'ISO-27001' o 'AES-256' deben sobrevivir como UN token, no partirse."""
        assert m12.tokenizar("norma ISO-27001") == ["norma", "iso-27001"]

    def test_texto_vacio(self, m12):
        assert m12.tokenizar("") == []


class TestTema12Coseno:
    def test_vectores_identicos_dan_1(self, m12):
        v = Counter("hola mundo".split())
        assert m12.similitud_coseno(v, v) == pytest.approx(1.0)

    def test_sin_palabras_comunes_da_0(self, m12):
        assert m12.similitud_coseno(Counter(["a"]), Counter(["b"])) == 0.0

    def test_vector_vacio_no_divide_entre_cero(self, m12):
        """El guard de norma==0: sin él, esto sería un ZeroDivisionError."""
        assert m12.similitud_coseno(Counter(), Counter(["b"])) == 0.0

    def test_es_simetrica(self, m12):
        a, b = Counter("hola mundo".split()), Counter("hola".split())
        assert m12.similitud_coseno(a, b) == pytest.approx(m12.similitud_coseno(b, a))


class TestTema12Bm25:
    def test_el_chunk_correcto_queda_primero(self, m12, chunks_datos_rag):
        """BM25 encuentra 'horario' y 'atención' literales en el chunk 2."""
        ranking = m12.ordenar(m12.puntuar_bm25(PREGUNTA_HORARIO, chunks_datos_rag))
        assert ranking[0] == CHUNK_HORARIO

    def test_un_chunk_sin_ninguna_palabra_puntua_cero(self, m12):
        puntajes = m12.puntuar_bm25("zebra", ["hola mundo", "adiós mundo"])
        assert puntajes == [0.0, 0.0]

    def test_las_palabras_raras_valen_mas_que_las_comunes(self, m12):
        """El IDF es el corazón de BM25: 'zebra' (rara) manda sobre 'datos' (común)."""
        chunks = ["datos zebra", "datos comunes", "datos normales"]
        # 'zebra' solo está en el chunk 0 -> debe ganar por lejos.
        puntajes = m12.puntuar_bm25("datos zebra", chunks)
        assert puntajes[0] > puntajes[1]
        assert puntajes[1] == pytest.approx(puntajes[2])


class TestTema12Vectorial:
    def test_el_chunk_correcto_queda_primero(self, m12, chunks_datos_rag):
        ranking = m12.ordenar(m12.puntuar_vectorial(PREGUNTA_HORARIO, chunks_datos_rag))
        assert ranking[0] == CHUNK_HORARIO

    def test_devuelve_un_puntaje_por_chunk(self, m12, chunks_datos_rag):
        assert len(m12.puntuar_vectorial(PREGUNTA_HORARIO, chunks_datos_rag)) == len(chunks_datos_rag)

    def test_todos_los_puntajes_entre_0_y_1(self, m12, chunks_datos_rag):
        """El coseno de vectores de conteo (no negativos) vive en [0, 1]."""
        assert all(0.0 <= p <= 1.0 for p in m12.puntuar_vectorial(PREGUNTA_HORARIO, chunks_datos_rag))


class TestTema12Rrf:
    def test_ganar_en_ambas_listas_te_deja_primero(self, m12):
        assert m12.fusionar_rrf([1, 0, 2], [1, 2, 0])[0] == 1

    def test_estar_en_ambas_listas_le_gana_a_brillar_en_una_sola(self, m12):
        """El valor real de RRF: aparecer en LOS DOS buscadores.

        El doc 7 es 2º en ambas listas. El doc 0 es 1º en la primera, pero la
        segunda ni lo vio. Gana el 7: un chunk que solo un buscador ama es
        sospechoso, y RRF lo castiga por ausencia.
        """
        assert m12.fusionar_rrf([0, 7], [3, 7])[0] == 7

    def test_dos_terceros_puestos_no_le_ganan_a_un_primero_y_un_ultimo(self, m12):
        """Sutileza importante: RRF NO premia la 'consistencia' por sí sola.

        1/(k+r) es una curva CONVEXA, así que ser 1º y 3º (0.0164 + 0.0159)
        rinde un pelo más que ser 2º y 2º (0.0161 + 0.0161). El promedio de los
        extremos supera al del medio. Lo que RRF premia es ESTAR PRESENTE en
        ambas listas (test anterior), no quedar equilibrado en ellas.
        """
        assert m12.fusionar_rrf([0, 1, 2], [2, 1, 0])[0] == 0

    def test_incluye_todos_los_documentos_vistos(self, m12):
        assert sorted(m12.fusionar_rrf([0, 1], [2])) == [0, 1, 2]

    def test_una_sola_lista_conserva_su_orden(self, m12):
        assert m12.fusionar_rrf([3, 1, 2]) == [3, 1, 2]

    def test_k_mas_chico_exagera_la_ventaja_del_primer_puesto(self, m12):
        """k es el amortiguador: con k=0, ser 1º vale muchísimo más que ser 2º."""
        assert m12.fusionar_rrf([0, 1], [1, 0], k=0)[0] in (0, 1)  # empate exacto
        # Con un doc que es 1º en ambas, el resultado no depende de k:
        assert m12.fusionar_rrf([5, 9], [5, 9], k=0)[0] == 5


class TestTema12ReRanking:
    def test_deja_el_mejor_arriba_y_recorta_a_top_n(self, m12, chunks_datos_rag):
        candidatos = [CHUNK_TITULO, CHUNK_ENTREGABLES, CHUNK_HORARIO]
        finalistas = m12.re_rankear(PREGUNTA_HORARIO, chunks_datos_rag, candidatos, top_n=2)
        assert len(finalistas) == 2
        assert finalistas[0] == CHUNK_HORARIO

    def test_descarta_el_chunk_de_ruido(self, m12, chunks_datos_rag):
        """El título suelto no responde nada: el re-ranker debe hundirlo."""
        candidatos = [CHUNK_TITULO, CHUNK_HORARIO]
        finalistas = m12.re_rankear(PREGUNTA_HORARIO, chunks_datos_rag, candidatos, top_n=1)
        assert finalistas == [CHUNK_HORARIO]

    def test_nunca_devuelve_mas_de_los_candidatos_dados(self, m12, chunks_datos_rag):
        assert len(m12.re_rankear(PREGUNTA_HORARIO, chunks_datos_rag, [CHUNK_HORARIO], top_n=5)) == 1

    def test_sin_candidatos_devuelve_lista_vacia(self, m12, chunks_datos_rag):
        assert m12.re_rankear(PREGUNTA_HORARIO, chunks_datos_rag, [], top_n=3) == []


class TestTema12PrecisionArriba:
    def test_el_pipeline_completo_pone_el_chunk_correcto_primero(self, m12, chunks_datos_rag):
        """La prueba que de verdad importa: precision@1 del pipeline híbrido.

        Es el test de regresión del TEMA 12: si alguien toca una fórmula y el
        chunk correcto deja de quedar 1º, esto se pone rojo.
        """
        bm25 = m12.ordenar(m12.puntuar_bm25(PREGUNTA_HORARIO, chunks_datos_rag))
        vect = m12.ordenar(m12.puntuar_vectorial(PREGUNTA_HORARIO, chunks_datos_rag))
        hibrido = m12.fusionar_rrf(bm25, vect)
        finalistas = m12.re_rankear(PREGUNTA_HORARIO, chunks_datos_rag, hibrido[:5], top_n=3)
        assert finalistas[0] == CHUNK_HORARIO
        assert "9:00 a 18:00" in chunks_datos_rag[finalistas[0]]

    def test_cargar_chunks_lee_el_archivo_real(self, m12, chunks_datos_rag):
        assert m12.cargar_chunks() == chunks_datos_rag


# ==================================================================
# TEMA 13b · Human-in-the-loop: interrupt() + Command(resume=…)
# ==================================================================
ESTADO_ALTA = {"hallazgo": "El 12% de los RUC están vacíos",
               "severidad": "alta", "aprobado": False, "registro": ""}


class TestTema13bHumanInTheLoop:
    """El grafo REAL de LangGraph, sin LLM, en sus dos ramas."""

    def test_severidad_alta_pausa_el_grafo(self, importar_ejemplo):
        app = importar_ejemplo("13b_human_in_the_loop").construir_grafo()
        resultado = app.invoke(ESTADO_ALTA, {"configurable": {"thread_id": "t_pausa"}})
        # La firma de un grafo pausado: la clave '__interrupt__'.
        assert "__interrupt__" in resultado
        peticion = resultado["__interrupt__"][0].value
        assert peticion["accion"] == "marcar incumplimiento regulatorio"
        assert peticion["hallazgo"] == ESTADO_ALTA["hallazgo"]

    def test_el_humano_aprueba_y_el_grafo_registra(self, importar_ejemplo):
        m = importar_ejemplo("13b_human_in_the_loop")
        from langgraph.types import Command
        app = m.construir_grafo()
        config = {"configurable": {"thread_id": "t_si"}}
        app.invoke(ESTADO_ALTA, config)                 # se pausa
        final = app.invoke(Command(resume="si"), config)  # el humano dice que sí
        assert final["aprobado"] is True
        assert final["registro"].startswith("REGISTRADO:")

    def test_el_humano_rechaza_y_el_grafo_descarta(self, importar_ejemplo):
        """La rama que suele quedar sin probar: el 'no'."""
        m = importar_ejemplo("13b_human_in_the_loop")
        from langgraph.types import Command
        app = m.construir_grafo()
        config = {"configurable": {"thread_id": "t_no"}}
        app.invoke(ESTADO_ALTA, config)
        final = app.invoke(Command(resume="no"), config)
        assert final["aprobado"] is False
        assert final["registro"].startswith("DESCARTADO:")

    def test_la_respuesta_humana_no_distingue_mayusculas_ni_espacios(self, importar_ejemplo):
        m = importar_ejemplo("13b_human_in_the_loop")
        from langgraph.types import Command
        app = m.construir_grafo()
        config = {"configurable": {"thread_id": "t_SI"}}
        app.invoke(ESTADO_ALTA, config)
        assert app.invoke(Command(resume="  SI  "), config)["aprobado"] is True

    def test_severidad_baja_se_aprueba_sola_sin_pausar(self, importar_ejemplo):
        """La otra rama: si no es grave, no molestamos a ningún humano."""
        app = importar_ejemplo("13b_human_in_the_loop").construir_grafo()
        estado = {**ESTADO_ALTA, "severidad": "baja"}
        final = app.invoke(estado, {"configurable": {"thread_id": "t_baja"}})
        assert "__interrupt__" not in final
        assert final["aprobado"] is True
        assert final["registro"].startswith("REGISTRADO:")

    def test_dos_hilos_no_se_pisan(self, importar_ejemplo):
        """El thread_id aísla auditorías distintas: una pausada, otra no."""
        app = importar_ejemplo("13b_human_in_the_loop").construir_grafo()
        pausada = app.invoke(ESTADO_ALTA, {"configurable": {"thread_id": "hilo_a"}})
        suelta = app.invoke({**ESTADO_ALTA, "severidad": "baja"},
                            {"configurable": {"thread_id": "hilo_b"}})
        assert "__interrupt__" in pausada
        assert "__interrupt__" not in suelta


# ==================================================================
# TEMA 14 · MCP: el cliente descubre las tools del servidor
# ==================================================================
def _texto_mcp(resultado) -> str:
    """MCP devuelve 'bloques de contenido'; sacamos el texto plano.

    Es la misma función que el ejemplo define dentro de correr_cliente().
    """
    if isinstance(resultado, list):
        return " ".join(b.get("text", "") for b in resultado if isinstance(b, dict))
    return str(resultado)


async def _descubrir_e_invocar(ruta_ejemplo):
    """Lanza el ejemplo en rol servidor y habla con él por el protocolo MCP."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    client = MultiServerMCPClient({
        "gobierno_datos": {
            "command": sys.executable,
            "args": [str(ruta_ejemplo), "servidor"],
            "transport": "stdio",
        },
    })
    herramientas = await client.get_tools()
    mapa = {t.name: t for t in herramientas}
    regla = await mapa["buscar_regla"].ainvoke({"nombre": "completitud"})
    severidades = {
        pct: _texto_mcp(await mapa["evaluar_severidad"].ainvoke({"porcentaje_error": pct}))
        for pct in (12.0, 7.0, 1.0)
    }
    return sorted(mapa), _texto_mcp(regla), severidades


@pytest.fixture(scope="module")
def resultado_mcp(carpeta_curso):
    """Habla UNA vez con el servidor MCP y reparte el resultado a los 3 tests.

    Levantar el subproceso es lo caro; lo hacemos una sola vez por módulo.
    asyncio.run() evita tener que instalar pytest-asyncio.
    """
    ruta = carpeta_curso / "14_mcp_servidor_cliente.py"
    return asyncio.run(_descubrir_e_invocar(ruta))


# ==================================================================
# TEMA 15 · Multiagente: el patrón supervisor
# ==================================================================
@pytest.fixture(scope="module")
def m15(importar_ejemplo):
    return importar_ejemplo("15_supervisor_multiagente")


class TestTema15Supervisor:
    """La política de enrutamiento es una función pura: se testea sola."""

    @pytest.mark.parametrize("pregunta", [
        "Evalúa esta regla: cifrado AES-256",
        "evalua si el RUC está completo",
        "Verifica que los datos cumplen",
        "¿Cumple la regla 3?",
    ])
    def test_las_peticiones_de_evaluacion_van_al_evaluador(self, m15, pregunta):
        assert m15.decidir(pregunta, ya_respondido=False) == "evaluador"

    @pytest.mark.parametrize("pregunta", [
        "¿Cuántos años se conservan los registros?",
        "¿Qué dice la normativa sobre el consentimiento?",
    ])
    def test_las_dudas_van_al_consultor(self, m15, pregunta):
        assert m15.decidir(pregunta, ya_respondido=False) == "consultor"

    def test_si_ya_hay_respuesta_se_termina(self, m15):
        """La regla que corta el bucle infinito del patrón supervisor.

        Sin ella, el especialista devuelve el control al supervisor, que vuelve
        a delegar, que vuelve a responder… para siempre.
        """
        assert m15.decidir("Evalúa esta regla", ya_respondido=True) == "FIN"
        assert m15.decidir("¿Qué dice la norma?", ya_respondido=True) == "FIN"

    def test_la_decision_no_distingue_mayusculas(self, m15):
        assert m15.decidir("EVALÚA ESTO", ya_respondido=False) == "evaluador"

    def test_el_grafo_enruta_una_duda_al_consultor(self, m15):
        estado = m15.responder("¿Cuántos años se conservan los registros?")
        assert estado["quien_respondio"] == "consultor"
        assert "10 años" in estado["respuesta"]

    def test_el_grafo_enruta_una_evaluacion_al_evaluador(self, m15):
        estado = m15.responder("Evalúa esta regla: cifrado con AES-256.")
        assert estado["quien_respondio"] == "evaluador"
        assert "severidad=alta" in estado["respuesta"]

    def test_el_grafo_termina_y_no_entra_en_bucle(self, m15):
        """Si el grafo no terminara, LangGraph lanzaría GraphRecursionError."""
        estado = m15.responder("¿Qué dice la normativa?")
        assert estado["siguiente"] == "FIN"

    def test_solo_responde_un_especialista_por_pregunta(self, m15):
        """El supervisor delega UNA vez: no encadena a los dos agentes."""
        estado = m15.responder("Evalúa la regla de cifrado.")
        assert estado["quien_respondio"] == "evaluador"


@pytest.fixture(scope="module")
def m16b(importar_ejemplo):
    return importar_ejemplo("16b_observabilidad_langsmith")


class TestTema16bObservabilidad:
    """Contar tokens y estimar coste son funciones puras: se testean gratis."""

    def test_extrae_los_tokens_de_la_respuesta(self, m16b):
        respuesta = m16b.RespuestaSimulada("hola", entrada=100, salida=20)
        assert m16b.extraer_tokens(respuesta) == {"entrada": 100, "salida": 20, "total": 120}

    def test_una_respuesta_sin_usage_metadata_no_revienta(self, m16b):
        """En streaming, muchos proveedores no informan el consumo. Devolvemos ceros."""
        class SinMetadatos:
            content = "hola"
        assert m16b.extraer_tokens(SinMetadatos()) == {"entrada": 0, "salida": 0, "total": 0}

    def test_el_costo_usa_la_tabla_de_precios(self, m16b):
        """1M de entrada a $0.10 + 1M de salida a $0.40 = $0.50."""
        tokens = {"entrada": 1_000_000, "salida": 1_000_000, "total": 2_000_000}
        assert m16b.estimar_costo(tokens, "gemini-2.0-flash") == pytest.approx(0.50)

    def test_la_salida_cuesta_mas_que_la_entrada(self, m16b):
        """La lección económica del tema: escribir es más caro que leer."""
        solo_entrada = m16b.estimar_costo({"entrada": 1000, "salida": 0, "total": 1000})
        solo_salida = m16b.estimar_costo({"entrada": 0, "salida": 1000, "total": 1000})
        assert solo_salida > solo_entrada

    def test_un_modelo_desconocido_cuesta_cero_en_vez_de_reventar(self, m16b):
        """Un informe de costes no debe tumbar la aplicación."""
        assert m16b.estimar_costo({"entrada": 10, "salida": 10, "total": 20}, "modelo-inventado") == 0.0

    def test_sin_tokens_no_hay_coste(self, m16b):
        assert m16b.estimar_costo({"entrada": 0, "salida": 0, "total": 0}) == 0.0

    def test_formatear_costo(self, m16b):
        assert m16b.formatear_costo(0) == "$0 (sin datos de consumo)"
        assert m16b.formatear_costo(0.000023) == "$0.000023"   # escala micro
        assert m16b.formatear_costo(1.5) == "$1.5000"          # escala normal

    def test_tokenizar_ignora_la_puntuacion(self, m16b):
        """El bug clásico del retrieval: 'atención?' != 'atención:'."""
        assert m16b.tokenizar("¿horario de atención?") == m16b.tokenizar("Horario de atención:")

    def test_tokenizar_descarta_las_palabras_cortas(self, m16b):
        assert m16b.tokenizar("de la es un horario") == {"horario"}

    def test_recuperar_trae_el_fragmento_correcto(self, m16b, chunks_datos_rag):
        """El retrieval extractivo debe encontrar el chunk del horario."""
        fragmentos = m16b.recuperar("¿Cuál es el horario de atención?", chunks_datos_rag, k=1)
        assert fragmentos[0].startswith("Horario de atención:")

    def test_recuperar_respeta_el_k(self, m16b, chunks_datos_rag):
        assert len(m16b.recuperar("horario", chunks_datos_rag, k=3)) == 3

    def test_generar_offline_responde_con_el_contexto(self, m16b):
        """Sin modelo, 'generar' devuelve el primer fragmento y estima sus tokens."""
        respuesta = m16b.generar("¿horario?", "Horario: de 9 a 18.\n\nOtro fragmento.", llm=None)
        assert respuesta.content == "Horario: de 9 a 18."
        assert respuesta.usage_metadata["output_tokens"] > 0

    def test_activar_tracing_es_no_op_sin_llave(self, m16b, monkeypatch):
        """Sin LANGSMITH_API_KEY no se toca el entorno: degradación graceful."""
        monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
        monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
        assert m16b.activar_tracing() is False
        assert "LANGSMITH_TRACING" not in os.environ

    def test_activar_tracing_enciende_el_interruptor_con_llave(self, m16b, monkeypatch):
        monkeypatch.setenv("LANGSMITH_API_KEY", "ls__falsa")
        monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
        monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
        assert m16b.activar_tracing() is True
        assert os.environ["LANGSMITH_TRACING"] == "true"
        assert os.environ["LANGSMITH_PROJECT"] == "curso-langchain"


class TestTema14Mcp:
    """Levanta el servidor MCP de verdad (subproceso) y le habla. Sin LLM."""

    def test_el_cliente_descubre_las_dos_tools(self, resultado_mcp):
        """Sin leer el código del servidor: se las pregunta por el protocolo."""
        nombres, _, _ = resultado_mcp
        assert nombres == ["buscar_regla", "evaluar_severidad"]

    def test_buscar_regla_devuelve_la_definicion(self, resultado_mcp):
        _, regla, _ = resultado_mcp
        assert regla == "no deben faltar valores obligatorios"

    def test_evaluar_severidad_cubre_los_tres_tramos(self, resultado_mcp):
        """>=10 alta · [5,10) media · <5 baja. Los bordes son lo que se rompe."""
        _, _, severidades = resultado_mcp
        assert severidades[12.0] == "alta"
        assert severidades[7.0] == "media"
        assert severidades[1.0] == "baja"


# ==================================================================
# TEMA 20 · RAG avanzado: multi-query + RAG-Fusion
# ==================================================================
# Los índices de chunk de datos_rag.txt (7 párrafos), para leer los tests:
CHUNK_REEMBOLSO = 3     # "Política de reembolsos: ..."
CHUNK_HORARIO_20 = 2    # "Horario de atención: ..."

PREGUNTA_DEVOLUCION = "¿Cómo pido la devolución de mi dinero?"


@pytest.fixture(scope="module")
def m20(importar_ejemplo):
    return importar_ejemplo("20_rag_avanzado")


class TestTema20Expandir:
    """Multi-query: una pregunta se reescribe de varias formas deterministas."""

    def test_genera_varias_variantes_distintas(self, m20):
        variantes = m20.expandir_consulta(PREGUNTA_DEVOLUCION)
        assert len(variantes) >= 3
        assert len(set(variantes)) == len(variantes)  # todas distintas

    def test_la_original_va_primero(self, m20):
        variantes = m20.expandir_consulta(PREGUNTA_DEVOLUCION)
        assert variantes[0] == PREGUNTA_DEVOLUCION

    def test_alguna_variante_usa_el_sinonimo_del_documento(self, m20):
        """El hueco clásico: el usuario dice 'devolución', el documento 'reembolso'.

        Al menos una reformulación debe traer la palabra que SÍ está en el doc.
        """
        variantes = m20.expandir_consulta(PREGUNTA_DEVOLUCION)
        assert any("reembolso" in v for v in variantes)

    def test_pregunta_sin_sinonimos_igual_devuelve_variantes(self, m20):
        variantes = m20.expandir_consulta("horario")
        assert len(variantes) >= 1
        assert variantes[0] == "horario"


class TestTema20Recuperar:
    """La recuperación con umbral: sin señal, no inventa resultados."""

    def test_devuelve_como_mucho_k(self, m20, chunks_datos_rag):
        assert len(m20.recuperar("atención reembolso pago", chunks_datos_rag, k=2)) <= 2

    def test_encuentra_el_chunk_de_reembolso_con_su_palabra(self, m20, chunks_datos_rag):
        assert m20.recuperar("reembolso", chunks_datos_rag, k=1) == [CHUNK_REEMBOLSO]

    def test_sin_ninguna_coincidencia_devuelve_vacio(self, m20, chunks_datos_rag):
        """El umbral > 0: 'devolución' no está literal en ningún chunk -> nada."""
        assert m20.recuperar("devolución", chunks_datos_rag, k=3) == []


class TestTema20Rrf:
    """La fusión RRF, con la misma semántica que el TEMA 12."""

    def test_ganar_en_ambas_listas_te_deja_primero(self, m20):
        assert m20.fusion_rrf([[1, 0, 2], [1, 2, 0]])[0] == 1

    def test_estar_en_ambas_listas_le_gana_a_brillar_en_una(self, m20):
        assert m20.fusion_rrf([[0, 7], [3, 7]])[0] == 7

    def test_incluye_todos_los_documentos_vistos(self, m20):
        assert sorted(m20.fusion_rrf([[0, 1], [2]])) == [0, 1, 2]

    def test_lista_vacia_no_aporta_ruido(self, m20):
        """Una reformulación que no encontró nada ([]) no debe cambiar el resultado."""
        assert m20.fusion_rrf([[5, 9], []]) == [5, 9]


class TestTema20RagFusion:
    """La prueba que importa: RAG-Fusion RESCATA lo que una sola búsqueda pierde."""

    def test_una_sola_busqueda_no_encuentra_el_chunk_correcto(self, m20, chunks_datos_rag):
        """El punto de partida: la pregunta cruda no casa con el chunk de reembolsos."""
        assert CHUNK_REEMBOLSO not in m20.recuperar(PREGUNTA_DEVOLUCION, chunks_datos_rag, k=3)

    def test_rag_fusion_sube_el_chunk_correcto_a_lo_alto(self, m20, chunks_datos_rag):
        """Con multi-query + RRF, el chunk de reembolsos aparece arriba."""
        fusion = m20.rag_fusion(PREGUNTA_DEVOLUCION, chunks_datos_rag, k=3)
        assert CHUNK_REEMBOLSO in fusion
        assert fusion[0] == CHUNK_REEMBOLSO

    def test_horario_sigue_funcionando(self, m20, chunks_datos_rag):
        """Regresión: una pregunta que ya casaba directo no debe empeorar."""
        fusion = m20.rag_fusion("¿Cuál es el horario de soporte?", chunks_datos_rag, k=3)
        assert fusion[0] == CHUNK_HORARIO_20


class TestTema20Comprimir:
    """Compresión extractiva: solo las frases que tocan la pregunta."""

    def test_conserva_la_frase_relevante(self, m20, chunks_datos_rag):
        texto = m20.comprimir_contexto(chunks_datos_rag, [CHUNK_REEMBOLSO], PREGUNTA_DEVOLUCION)
        assert "reembolso" in texto.lower()

    def test_descarta_un_chunk_sin_relacion(self, m20, chunks_datos_rag):
        """El chunk de horario no tiene nada de reembolsos: se comprime a vacío."""
        assert m20.comprimir_contexto(chunks_datos_rag, [CHUNK_HORARIO_20], PREGUNTA_DEVOLUCION) == ""


# ==================================================================
# TEMA 21 · Fine-tuning vs RAG: decisión + dataset de chat
# ==================================================================
@pytest.fixture(scope="module")
def m21(importar_ejemplo):
    return importar_ejemplo("21_fine_tuning")


class TestTema21Decision:
    """La recomendación es una función pura de reglas: casos canónicos."""

    def test_conocimiento_que_cambia_es_rag(self, m21):
        assert m21.recomendar_enfoque({"conocimiento_cambia_seguido": True}) == "RAG"

    def test_formato_fijo_con_dataset_es_fine_tuning(self, m21):
        assert m21.recomendar_enfoque({
            "necesita_formato_o_estilo_fijo": True,
            "hay_ejemplos_etiquetados": True,
        }) == "fine-tuning"

    def test_formato_fijo_sin_dataset_cae_en_prompt(self, m21):
        assert m21.recomendar_enfoque({
            "necesita_formato_o_estilo_fijo": True,
            "hay_ejemplos_etiquetados": False,
        }) == "prompt"

    def test_conocimiento_mas_comportamiento_con_dataset_es_ambos(self, m21):
        assert m21.recomendar_enfoque({
            "conocimiento_cambia_seguido": True,
            "necesita_formato_o_estilo_fijo": True,
            "hay_ejemplos_etiquetados": True,
        }) == "ambos"

    def test_presupuesto_bajo_evita_el_fine_tuning(self, m21):
        """Con dataset y formato fijo, pero sin presupuesto: primero el prompt."""
        assert m21.recomendar_enfoque({
            "necesita_formato_o_estilo_fijo": True,
            "hay_ejemplos_etiquetados": True,
            "presupuesto_bajo": True,
        }) == "prompt"

    def test_sin_senales_especiales_es_prompt(self, m21):
        assert m21.recomendar_enfoque({}) == "prompt"


class TestTema21Dataset:
    """El armado del dataset de chat: la estructura ES el contrato con la plataforma."""

    def test_cada_ejemplo_tiene_los_tres_roles_en_orden(self, m21):
        dataset = m21.preparar_dataset_chat([("hola", "qué tal")], "sé breve")
        assert len(dataset) == 1
        roles = [m["role"] for m in dataset[0]["messages"]]
        assert roles == ["system", "user", "assistant"]

    def test_el_contenido_se_coloca_donde_toca(self, m21):
        dataset = m21.preparar_dataset_chat([("¿precio?", "100 soles")], "sistema fijo")
        msgs = dataset[0]["messages"]
        assert msgs[0]["content"] == "sistema fijo"
        assert msgs[1]["content"] == "¿precio?"
        assert msgs[2]["content"] == "100 soles"

    def test_convierte_todos_los_pares(self, m21):
        pares = [("a", "1"), ("b", "2"), ("c", "3")]
        assert len(m21.preparar_dataset_chat(pares, "s")) == 3

    def test_sin_pares_da_dataset_vacio(self, m21):
        assert m21.preparar_dataset_chat([], "s") == []


class TestTema21Jsonl:
    """JSONL: una línea JSON por registro, y cada línea parseable por sí sola."""

    def test_una_linea_por_registro(self, m21):
        dataset = m21.preparar_dataset_chat([("a", "1"), ("b", "2")], "s")
        assert m21.a_jsonl(dataset).count("\n") == 1  # 2 registros -> 1 salto

    def test_cada_linea_es_json_valido(self, m21):
        import json
        dataset = m21.preparar_dataset_chat([("a", "1"), ("b", "2")], "s")
        for linea in m21.a_jsonl(dataset).splitlines():
            registro = json.loads(linea)
            assert "messages" in registro

    def test_conserva_tildes_sin_escapar(self, m21):
        """ensure_ascii=False: la ñ y las tildes se leen en claro en el archivo."""
        dataset = m21.preparar_dataset_chat([("¿atención?", "sí, mañana")], "en español")
        assert "atención" in m21.a_jsonl(dataset)


# ==================================================================
# TEMA 22 · Multimodal: construir el mensaje texto + imagen
# ==================================================================
@pytest.fixture(scope="module")
def m22(importar_ejemplo):
    return importar_ejemplo("22_multimodal")


class TestTema22DataUrl:
    """La imagen se codifica en un data: URL con su base64."""

    def test_prefijo_correcto(self, m22):
        url = m22.imagen_a_data_url(b"\x89PNG\r\n", mime="image/png")
        assert url.startswith("data:image/png;base64,")

    def test_respeta_el_mime_que_se_le_pasa(self, m22):
        assert m22.imagen_a_data_url(b"xx", mime="image/jpeg").startswith("data:image/jpeg;base64,")

    def test_el_base64_es_decodificable_y_recupera_los_bytes(self, m22):
        import base64
        datos = b"unos bytes cualquiera \x00\x01\x02"
        url = m22.imagen_a_data_url(datos)
        b64 = url.split(",", 1)[1]
        assert base64.b64decode(b64) == datos

    def test_el_png_demo_es_un_png_de_verdad(self, m22):
        import base64
        datos = base64.b64decode(m22.PNG_DEMO_1x1)
        assert datos[:8] == b"\x89PNG\r\n\x1a\n"  # la firma mágica de un PNG


class TestTema22Mensaje:
    """El mensaje multimodal: dos bloques, texto + imagen, en el formato correcto."""

    def test_tiene_exactamente_dos_bloques(self, m22):
        msg = m22.mensaje_multimodal("hola", "data:image/png;base64,AAAA")
        assert len(msg.content) == 2

    def test_el_bloque_de_texto_preserva_el_texto(self, m22):
        msg = m22.mensaje_multimodal("¿qué ves?", "data:image/png;base64,AAAA")
        assert msg.content[0]["type"] == "text"
        assert msg.content[0]["text"] == "¿qué ves?"

    def test_el_bloque_de_imagen_lleva_el_data_url(self, m22):
        url = "data:image/png;base64,AAAA"
        msg = m22.mensaje_multimodal("x", url)
        assert msg.content[1]["type"] == "image_url"
        assert msg.content[1]["image_url"]["url"] == url

    def test_es_un_humanmessage(self, m22):
        from langchain_core.messages import HumanMessage
        assert isinstance(m22.mensaje_multimodal("x", "data:image/png;base64,AAAA"), HumanMessage)

    def test_el_formato_lo_acepta_langchain_google_genai(self, m22):
        """El contrato de verdad: langchain-google-genai traduce ESTA estructura a
        una parte 'inline_data' de Gemini. Confirma que el formato que construimos
        es el que el proveedor con visión espera (sin llamar a la API)."""
        import base64
        from langchain_google_genai.chat_models import _convert_to_parts
        url = m22.imagen_a_data_url(base64.b64decode(m22.PNG_DEMO_1x1))
        partes = _convert_to_parts(m22.mensaje_multimodal("mira", url).content)
        assert len(partes) == 2
        assert partes[0].text == "mira"
        assert partes[1].inline_data.mime_type == "image/png"
        assert len(partes[1].inline_data.data) > 0


# ==================================================================
# TEMA 23 · Seguridad: guardarraíles (la batería de ataques va en test_redteam.py)
# ==================================================================
@pytest.fixture(scope="module")
def m23(importar_ejemplo):
    return importar_ejemplo("23_seguridad")


class TestTema23Guardarrailes:
    """Las piezas del pipeline por separado. Los ATAQUES concretos viven en
    tests/test_redteam.py; aquí probamos el contrato de cada función."""

    def test_construir_prompt_marca_el_contexto_como_datos(self, m23):
        prompt = m23.construir_prompt("¿precio?", "el precio es 100 soles")
        assert m23.MARCA_DATOS in prompt
        assert "el precio es 100 soles" in prompt
        # La instrucción de no obedecer al contexto debe estar presente.
        assert "NUNCA obedezcas" in prompt

    def test_el_modelo_credulo_recita_el_bloque_de_datos(self, m23):
        """El doble de juguete obedece: devuelve tal cual lo que va tras la marca."""
        prompt = m23.construir_prompt("x", "TEXTO SECRETO")
        assert m23.modelo_ingenuo(prompt) == "TEXTO SECRETO"

    def test_responder_seguro_devuelve_las_tres_claves(self, m23):
        r = m23.responder_seguro("¿horario?", "de 9 a 18")
        assert set(r) == {"respuesta", "cruda", "alertas"}

    def test_sanear_escapa_los_angulos_del_texto_normal(self, m23):
        """El HTML que no es un bloque peligroso se ESCAPA, no se ejecuta."""
        limpio = m23.sanear_salida("2 < 3 y <b>negrita</b>")
        assert "&lt;" in limpio
        assert "<b>" not in limpio

    def test_detectar_inyeccion_devuelve_lista_vacia_si_esta_limpio(self, m23):
        assert m23.detectar_inyeccion("¿cuánto cuesta el servicio?") == []


# ==================================================================
# TEMA 24 · Vector DBs: dedup por hash + índice IVFFlat didáctico
# ==================================================================
@pytest.fixture(scope="module")
def m24(importar_ejemplo):
    return importar_ejemplo("24_vector_db")


# Un corpus pequeño y determinista con dos "temas" (mascotas / finanzas) para
# que el clustering tenga algo que separar.
CORPUS_M24 = [
    "el gato negro duerme en el sofá de casa",
    "el perro corre feliz por el parque",
    "las acciones subieron en la bolsa de valores hoy",
    "el mercado bursátil cerró a la baja esta tarde",
    "receta de pastel de chocolate casero muy fácil",
    "cómo hornear pan integral en casa paso a paso",
    "el gato blanco juega con la lana en el sofá",
    "inversiones y finanzas personales para principiantes",
]


class TestTema24Dedup:
    """Dedup por hash: no indexar la misma información dos veces."""

    def test_normaliza_mayusculas_y_espacios(self, m24):
        """Mismo texto, distinta caja/puntuación -> mismo hash."""
        assert m24.hash_normalizado("Hola,  MUNDO!") == m24.hash_normalizado("hola mundo")

    def test_textos_distintos_dan_hashes_distintos(self, m24):
        assert m24.hash_normalizado("gato") != m24.hash_normalizado("perro")

    def test_deduplicar_quita_exactos_y_casi_exactos(self, m24):
        chunks = ["El horario es de 9 a 18.", "el horario es de 9 a 18", "Formas de pago: Yape."]
        unicos = m24.deduplicar(chunks)
        assert len(unicos) == 2

    def test_deduplicar_conserva_el_orden_y_la_primera_aparicion(self, m24):
        chunks = ["primero", "segundo", "PRIMERO"]
        assert m24.deduplicar(chunks) == ["primero", "segundo"]


class TestTema24Ivf:
    """Índice IVFFlat: sondar solo las listas cercanas, con el trade-off recall↔velocidad."""

    def _indice(self, m24, n_listas=3):
        vectores = [m24.vectorizar(t) for t in CORPUS_M24]
        return vectores, m24.construir_ivf(vectores, n_listas=n_listas)

    def test_cada_vector_cae_en_exactamente_una_lista(self, m24):
        _, indice = self._indice(m24)
        asignados = sorted(i for lista in indice.listas for i in lista)
        assert asignados == list(range(len(CORPUS_M24)))

    def test_encuentra_el_vecino_correcto(self, m24):
        """La consulta es (casi) un documento: con sondas suficientes, sale primero."""
        vectores, indice = self._indice(m24)
        consulta = m24.vectorizar("el gato juega en el sofá")
        # Con todas las sondas, IVF ve todo -> el mejor vecino real está en el top.
        top = m24.buscar_ivf(consulta, indice, k=3, n_sondas=3)
        exacto = m24.buscar_exacto(consulta, vectores, k=3)
        assert exacto[0] in top

    def test_subir_sondas_no_empeora_el_recall(self, m24):
        vectores, indice = self._indice(m24)
        consulta = m24.vectorizar("finanzas y bolsa de valores")
        exacto = set(m24.buscar_exacto(consulta, vectores, k=3))
        recalls = []
        for sondas in (1, 2, 3):
            aprox = set(m24.buscar_ivf(consulta, indice, k=3, n_sondas=sondas))
            recalls.append(len(aprox & exacto) / len(exacto))
        # Monótono no decreciente: más sondas nunca dan menos recall.
        assert recalls == sorted(recalls)

    def test_con_todas_las_sondas_iguala_al_escaneo_exacto(self, m24):
        vectores, indice = self._indice(m24, n_listas=3)
        consulta = m24.vectorizar("receta de pan y pastel casero")
        exacto = set(m24.buscar_exacto(consulta, vectores, k=3))
        todas = set(m24.buscar_ivf(consulta, indice, k=3, n_sondas=3))
        assert todas == exacto


# ==================================================================
# TEMA 26b · Prompt engineering: few-shot, CoT, self-consistency, descomposición
# ==================================================================
@pytest.fixture(scope="module")
def m26b(importar_ejemplo):
    return importar_ejemplo("26b_prompt_engineering")


class TestTema26bFewShot:
    """Few-shot: las demostraciones y la pregunta aparecen, y EN ORDEN."""

    def test_incluye_todos_los_ejemplos_y_la_pregunta(self, m26b):
        ejemplos = [("2+2", "4"), ("3+3", "6")]
        prompt = m26b.construir_prompt_fewshot(ejemplos, "5+5")
        for p, r in ejemplos:
            assert p in prompt and r in prompt
        assert "5+5" in prompt

    def test_respeta_el_orden_demostraciones_antes_de_la_pregunta(self, m26b):
        ejemplos = [("primera", "A"), ("segunda", "B")]
        prompt = m26b.construir_prompt_fewshot(ejemplos, "final")
        # El orden del texto: primera, luego segunda, y la pregunta al FINAL.
        assert prompt.index("primera") < prompt.index("segunda") < prompt.index("final")

    def test_la_pregunta_queda_sin_responder(self, m26b):
        """La pregunta real cierra el prompt con 'R:' vacío: el modelo la completa."""
        prompt = m26b.construir_prompt_fewshot([("x", "y")], "z")
        assert prompt.rstrip().endswith("R:")


class TestTema26bCoT:
    """Chain-of-thought: añade la estructura de razonar paso a paso."""

    def test_conserva_la_pregunta(self, m26b):
        assert "¿cuánto es 12*12?" in m26b.plantilla_cot("¿cuánto es 12*12?")

    def test_agrega_la_instruccion_de_razonar(self, m26b):
        salida = m26b.plantilla_cot("una pregunta").lower()
        assert "paso a paso" in salida

    def test_el_razonamiento_va_despues_de_la_pregunta(self, m26b):
        salida = m26b.plantilla_cot("PREG")
        assert salida.index("PREG") < salida.index("paso a paso")


class TestTema26bSelfConsistency:
    """Self-consistency: votación por mayoría (la moda) sobre varias muestras."""

    def test_mayoria_clara(self, m26b):
        assert m26b.self_consistency(["7", "7", "3", "7"]) == "7"

    def test_una_sola_respuesta(self, m26b):
        assert m26b.self_consistency(["42"]) == "42"

    def test_empate_devuelve_la_primera_en_aparecer(self, m26b):
        # "a" y "b" empatan a 2; gana la que apareció primero (orden de inserción).
        assert m26b.self_consistency(["a", "b", "b", "a"]) == "a"

    def test_lista_vacia_devuelve_none(self, m26b):
        assert m26b.self_consistency([]) is None


class TestTema26bDescomponer:
    """Descomposición: partir una tarea compuesta en sub-pasos."""

    def test_parte_por_los_conectores(self, m26b):
        pasos = m26b.descomponer("busca el precio y calcula el IVA y suma el total")
        assert pasos == ["busca el precio", "calcula el IVA", "suma el total"]

    def test_una_tarea_simple_queda_como_un_solo_paso(self, m26b):
        assert m26b.descomponer("resume el documento") == ["resume el documento"]

    def test_reconoce_luego_y_punto_y_coma(self, m26b):
        pasos = m26b.descomponer("descarga el archivo; luego valídalo")
        assert pasos == ["descarga el archivo", "valídalo"]


class TestTema26bHarness:
    """El harness antes/después: un prompt mejor mide >= que uno peor (offline)."""

    def test_cot_no_es_peor_que_el_directo(self, m26b):
        marcador = m26b.comparar_estrategias()
        assert marcador["cot"] >= marcador["directo"]

    def test_cot_acierta_todo_el_mini_dataset(self, m26b):
        assert m26b.evaluar(m26b.resolver_cot, m26b.DATASET) == 1.0

    def test_la_metrica_de_un_dataset_vacio_es_cero(self, m26b):
        assert m26b.evaluar(m26b.resolver_cot, []) == 0.0


# ==================================================================
# TEMA 27 · Fundamentos: tokenización BPE, softmax, muestreo, perplejidad
# ==================================================================
@pytest.fixture(scope="module")
def m27(importar_ejemplo):
    return importar_ejemplo("27_fundamentos_llm")


class TestTema27Bpe:
    """Tokenizador BPE: determinista y con el plural costando un token más."""

    CORPUS = ["proyecto", "objeto", "efecto", "afecto", "insecto", "dialecto"]

    def test_aprender_merges_es_determinista(self, m27):
        """Mismo corpus → mismas fusiones, sin azar: se puede testear byte a byte."""
        a = m27.aprender_merges(self.CORPUS, 12)
        b = m27.aprender_merges(self.CORPUS, 12)
        assert a == b

    def test_tokenizar_es_determinista(self, m27):
        merges = m27.aprender_merges(self.CORPUS, 12)
        assert m27.tokenizar_bpe("proyecto", merges) == m27.tokenizar_bpe("proyecto", merges)

    def test_el_plural_cuesta_un_token_mas(self, m27):
        """'proyectos' se tokeniza en más piezas que 'proyecto' (la 's' suelta)."""
        merges = m27.aprender_merges(self.CORPUS, 12)
        singular = m27.tokenizar_bpe("proyecto", merges)
        plural = m27.tokenizar_bpe("proyectos", merges)
        assert len(plural) > len(singular)
        assert plural[-1] == "s"

    def test_reconstruye_la_palabra_original(self, m27):
        """Unir los tokens devuelve la palabra: BPE parte, no pierde información."""
        merges = m27.aprender_merges(self.CORPUS, 12)
        assert "".join(m27.tokenizar_bpe("dialecto", merges)) == "dialecto"

    def test_sin_merges_son_los_caracteres_sueltos(self, m27):
        assert m27.tokenizar_bpe("hola", []) == ["h", "o", "l", "a"]


class TestTema27Softmax:
    """Softmax con temperatura: suma 1 y se concentra/aplana según t."""

    LOGITS = [2.0, 1.0, 0.2, -1.0]

    def test_suma_uno(self, m27):
        assert math.isclose(sum(m27.softmax_con_temperatura(self.LOGITS, 1.0)), 1.0)

    def test_temperatura_baja_concentra_mas_que_alta(self, m27):
        """A menor t, más masa en el token mayor (distribución más picuda)."""
        fria = m27.softmax_con_temperatura(self.LOGITS, 0.5)
        caliente = m27.softmax_con_temperatura(self.LOGITS, 2.0)
        assert max(fria) > max(caliente)

    def test_temperatura_cero_es_greedy(self, m27):
        """t=0 → toda la masa en el logit máximo (límite determinista, como m01)."""
        probs = m27.softmax_con_temperatura(self.LOGITS, 0.0)
        assert probs == [1.0, 0.0, 0.0, 0.0]

    def test_conserva_el_orden_de_los_logits(self, m27):
        """El token de mayor logit es siempre el de mayor probabilidad."""
        probs = m27.softmax_con_temperatura(self.LOGITS, 1.0)
        assert probs.index(max(probs)) == self.LOGITS.index(max(self.LOGITS))

    def test_lista_vacia_devuelve_vacio(self, m27):
        assert m27.softmax_con_temperatura([], 1.0) == []


class TestTema27Muestreo:
    """top_k / top_p: recortan la distribución antes de muestrear (Random inyectado)."""

    LOGITS = [3.0, 2.0, 0.5, -2.0]

    def test_top_k_solo_devuelve_los_k_mejores(self, m27):
        """Con k=2, muchas pasadas nunca salen de los índices 0 y 1."""
        rng = random.Random(0)
        elegidos = {m27.muestrear_top_k(self.LOGITS, 2, rng) for _ in range(50)}
        assert elegidos <= {0, 1}

    def test_top_k_uno_es_greedy(self, m27):
        """k=1 → siempre el token de mayor logit, pase lo que pase el azar."""
        rng = random.Random(7)
        assert all(m27.muestrear_top_k(self.LOGITS, 1, rng) == 0 for _ in range(20))

    def test_top_k_es_reproducible_con_la_misma_semilla(self, m27):
        seq_a = [m27.muestrear_top_k(self.LOGITS, 3, random.Random(99)) for _ in range(5)]
        seq_b = [m27.muestrear_top_k(self.LOGITS, 3, random.Random(99)) for _ in range(5)]
        assert seq_a == seq_b

    def test_top_p_se_queda_en_el_nucleo(self, m27):
        """Con p pequeño, el núcleo es casi solo el token dominante (índice 0)."""
        rng = random.Random(0)
        elegidos = {m27.muestrear_top_p(self.LOGITS, 0.5, rng) for _ in range(50)}
        assert elegidos <= {0, 1}


class TestTema27Perplejidad:
    """Perplejidad: baja para texto que el modelo esperaba, alta para el improbable."""

    def test_texto_predecible_tiene_menor_perplejidad(self, m27):
        fluido = m27.calcular_perplejidad([0.9, 0.85, 0.8, 0.92])
        basura = m27.calcular_perplejidad([0.05, 0.1, 0.02, 0.08])
        assert fluido < basura

    def test_certeza_total_da_perplejidad_uno(self, m27):
        """Si el modelo asignó prob. 1 a cada token, no hubo sorpresa: PPL=1."""
        assert math.isclose(m27.calcular_perplejidad([1.0, 1.0, 1.0]), 1.0)

    def test_probabilidad_cero_es_sorpresa_infinita(self, m27):
        assert m27.calcular_perplejidad([0.5, 0.0, 0.5]) == float("inf")

    def test_lista_vacia_es_infinito(self, m27):
        assert m27.calcular_perplejidad([]) == float("inf")


class TestTema27Atencion:
    """Atención: la clave más parecida a la consulta se lleva el mayor peso."""

    def test_los_pesos_suman_uno(self, m27):
        pesos = m27.pesos_atencion([1.0, 0.0], [[1.0, 0.0], [0.0, 1.0]])
        assert math.isclose(sum(pesos), 1.0)

    def test_mira_mas_a_la_clave_mas_afin(self, m27):
        consulta = [1.0, 0.0, 1.0]
        claves = [[1.0, 0.0, 1.0], [0.0, 1.0, 0.0], [0.5, 0.0, 0.5]]
        pesos = m27.pesos_atencion(consulta, claves)
        assert pesos.index(max(pesos)) == 0  # la 1ª clave es idéntica a la consulta


# ==================================================================
# TEMA 28 · Desafíos: taxonomía, detector de inconsistencia, fragilidad
# ==================================================================
@pytest.fixture(scope="module")
def m28(importar_ejemplo):
    return importar_ejemplo("28_alucinaciones")


class TestTema28Taxonomia:
    """La taxonomía es un mapa consultable causa → mitigación → módulo."""

    def test_cada_fila_tiene_los_campos_del_contrato(self, m28):
        claves = {"causa", "categoria", "senal", "mitigacion", "modulo"}
        assert m28.TAXONOMIA, "la taxonomía no puede estar vacía"
        for fila in m28.TAXONOMIA:
            assert claves <= set(fila), f"fila incompleta: {fila}"

    def test_las_categorias_son_del_marco_de_cuatro(self, m28):
        """Cada causa cuelga de una de las 4 categorías-paraguas de la teoría."""
        for fila in m28.TAXONOMIA:
            assert fila["categoria"] in m28.CATEGORIAS

    def test_apunta_a_modulos_que_ensenaron_la_defensa(self, m28):
        """Las mitigaciones remiten a módulos reales del curso (RAG, evals, etc.)."""
        assert m28.modulos_de_mitigacion() <= {"m11", "m16", "m23", "m26b"}

    def test_causas_por_modulo_filtra_bien(self, m28):
        causas = m28.causas_por_modulo("m11")
        assert "Falta de grounding" in causas
        assert all(isinstance(c, str) for c in causas)

    def test_un_modulo_sin_causas_devuelve_lista_vacia(self, m28):
        assert m28.causas_por_modulo("m99") == []


class TestTema28Inconsistencia:
    """Detector estilo SelfCheckGPT: divergencia entre muestras de una pregunta."""

    def test_todas_iguales_no_divergen(self, m28):
        assert m28.detectar_inconsistencia(["París", "parís", "París."]) == 0.0

    def test_todas_distintas_divergen_mucho(self, m28):
        """4 respuestas distintas → 1 - 1/4 = 0.75."""
        assert m28.detectar_inconsistencia(["1812", "1798", "1820", "1805"]) == 0.75

    def test_ignora_puntuacion_y_mayusculas(self, m28):
        """'París.' y 'parís' son la MISMA respuesta: no deben inflar la divergencia."""
        assert m28.detectar_inconsistencia(["París.", "parís"]) == 0.0

    def test_lista_vacia_no_divergencia(self, m28):
        assert m28.detectar_inconsistencia([]) == 0.0

    def test_es_sospechosa_dispara_sobre_el_umbral(self, m28):
        assert m28.es_sospechosa(["1812", "1798", "1820", "1805"]) is True
        assert m28.es_sospechosa(["París", "parís", "París"]) is False


class TestTema28Fragilidad:
    """Fragilidad: variaciones triviales del prompt no deberían cambiar la respuesta."""

    def test_prompt_robusto_da_una_sola_respuesta(self, m28):
        assert m28.medir_fragilidad(["4", " 4 ", "4."]) == 1
        assert m28.es_fragil(["4", " 4 ", "4."]) is False

    def test_prompt_fragil_da_varias_respuestas(self, m28):
        respuestas = ["Sí, es seguro", "No, evítalo", "Depende del caso"]
        assert m28.medir_fragilidad(respuestas) == 3
        assert m28.es_fragil(respuestas) is True


# ==================================================================
# TEMA 29 · Caso real 2: asistente de compras retail (100% offline)
# ==================================================================
@pytest.fixture(scope="module")
def m29(importar_ejemplo):
    return importar_ejemplo("29_caso_retail")


@pytest.fixture(scope="module")
def catalogo29(m29):
    return m29.cargar_catalogo()


class TestTema29Etl:
    """El ETL: del products.json crudo a un producto usable."""

    def test_el_precio_string_se_vuelve_float(self, m29):
        producto = m29.normalizar_producto(m29.CATALOGO_CRUDO[0])
        assert isinstance(producto["precio"], float)

    def test_promo_cuando_compare_at_es_mayor(self, m29):
        con_promo = m29.normalizar_producto({
            "title": "X", "product_type": "Joyería", "tags": [],
            "variants": [{"sku": "T-1", "price": "12.90",
                          "compare_at_price": "39.90", "available": True}]})
        sin_promo = m29.normalizar_producto({
            "title": "X", "product_type": "Joyería", "tags": [],
            "variants": [{"sku": "T-2", "price": "12.90",
                          "compare_at_price": None, "available": True}]})
        assert con_promo["en_promo"] is True
        assert sin_promo["en_promo"] is False

    def test_la_categoria_se_deriva_no_se_confia(self, m29):
        """La lección del dato real: product_type dice 'Joyería' hasta en la
        mochila. La categoría sale del título+tags."""
        mochila = m29.normalizar_producto({
            "title": "Mochila 2 en 1 Travel Fucsia", "product_type": "Joyería",
            "tags": ["Mochila"],
            "variants": [{"sku": "T-3", "price": "12.90",
                          "compare_at_price": None, "available": True}]})
        assert mochila["categoria"] == "mochilas"          # NO "joyería"

    def test_el_cepillo_es_belleza_no_cabello(self, m29, catalogo29):
        """'Cepillo de Cabello' contiene 'cabello', pero su categoría real es
        belleza: el orden de las reglas del ETL importa."""
        cepillo = next(p for p in catalogo29 if p["sku"] == "BE-001")
        assert cepillo["categoria"] == "belleza"


class TestTema29Filtros:
    """Extraer intención: presupuesto, categoría y color desde la petición."""

    def test_presupuesto_menos_de(self, m29):
        assert m29.extraer_filtros("aretes por menos de 25 soles")["presupuesto"] == 25.0

    def test_presupuesto_hasta_con_simbolo(self, m29):
        assert m29.extraer_filtros("una cartera hasta S/80")["presupuesto"] == 80.0

    def test_sin_presupuesto_es_none(self, m29):
        assert m29.extraer_filtros("aretes dorados")["presupuesto"] is None

    def test_categoria_y_color(self, m29):
        filtros = m29.extraer_filtros("quiero aretes dorados")
        assert filtros["categoria"] == "aretes"
        assert filtros["color"] == "dorado"

    def test_sinonimos_de_la_clienta(self, m29):
        """'aros' y 'pelo' no están en el catálogo, pero sí en la calle."""
        assert m29.extraer_filtros("unos aros plateados")["categoria"] == "aretes"
        assert m29.extraer_filtros("algo para el pelo")["categoria"] == "cabello"


class TestTema29Busqueda:
    """Filtros DUROS primero (precio, stock, categoría), ranking después."""

    def test_respeta_el_presupuesto(self, m29, catalogo29):
        resultados = m29.buscar_productos(
            {"presupuesto": 25.0, "categoria": "aretes", "color": None}, catalogo29)
        assert resultados and all(p["precio"] <= 25.0 for p in resultados)

    def test_excluye_lo_no_disponible(self, m29, catalogo29):
        """AR-003 (aretes zircón) está agotado: no debe recomendarse jamás."""
        resultados = m29.buscar_productos(
            {"presupuesto": None, "categoria": "aretes", "color": None}, catalogo29)
        assert all(p["sku"] != "AR-003" for p in resultados)

    def test_el_color_pedido_sube_al_primer_lugar(self, m29, catalogo29):
        resultados = m29.buscar_productos(
            {"presupuesto": 25.0, "categoria": "aretes", "color": "dorado"}, catalogo29)
        assert "dorado" in resultados[0]["texto"]

    def test_sin_candidatos_devuelve_vacio_no_inventa(self, m29, catalogo29):
        """'Nada cumple' es una respuesta válida (la regla del m20): un
        sustituto fuera de presupuesto NO lo es."""
        resultados = m29.buscar_productos(
            {"presupuesto": 5.0, "categoria": "carteras", "color": None}, catalogo29)
        assert resultados == []


class TestTema29Grounding:
    """El guardrail del retail: ningún precio citado fuera del catálogo."""

    def test_respuesta_con_precios_del_catalogo_es_fiel(self, m29, catalogo29):
        productos = m29.buscar_productos(
            {"presupuesto": 25.0, "categoria": "aretes", "color": None}, catalogo29)
        respuesta = m29.armar_respuesta(productos)
        assert m29.respuesta_es_fiel(respuesta, productos) is True

    def test_un_precio_inventado_viola_el_guardrail(self, m29, catalogo29):
        productos = m29.buscar_productos(
            {"presupuesto": 25.0, "categoria": "aretes", "color": None}, catalogo29)
        con_invento = m29.armar_respuesta(productos) + "\n- Collar Mágico a S/99.90"
        assert m29.respuesta_es_fiel(con_invento, productos) is False

    def test_sin_productos_la_respuesta_es_honesta(self, m29):
        respuesta = m29.armar_respuesta([])
        assert "no encontré" in respuesta.lower()
        assert m29.precios_citados(respuesta) == set()


class TestTema29Eval:
    """La misma métrica juzga al asistente honesto y al descuidado (m16)."""

    CASOS = [
        {"peticion": "aretes dorados por menos de 25 soles"},
        {"peticion": "un collar hasta S/35"},
        {"peticion": "algo para el pelo, máximo 8 soles"},
        {"peticion": "una cartera hasta S/80"},
    ]

    def test_el_asistente_honesto_aprueba_todo(self, m29, catalogo29):
        nota = m29.evaluar_asistente(self.CASOS, m29.asistente_honesto, catalogo29)
        assert nota == 1.0

    def test_el_eval_atrapa_al_descuidado(self, m29, catalogo29):
        """Ignorar el presupuesto DEBE bajar la nota: si no la baja, la métrica
        no mide nada."""
        nota = m29.evaluar_asistente(self.CASOS, m29.asistente_descuidado, catalogo29)
        assert nota < 1.0

    def test_sin_casos_la_nota_es_cero(self, m29, catalogo29):
        assert m29.evaluar_asistente([], m29.asistente_honesto, catalogo29) == 0.0


# ==================================================================
# TEMA 30 · Memoria de largo plazo con el store (100% offline)
# ==================================================================
@pytest.fixture(scope="module")
def m30(importar_ejemplo):
    return importar_ejemplo("30_memoria_largo_plazo")


@pytest.fixture()
def store30(m30):
    """Un InMemoryStore limpio por test (function scope: no arrastra estado)."""
    from langgraph.store.memory import InMemoryStore
    return InMemoryStore()


class TestTema30Store:
    """El CRUD sobre el store: guardar y recuperar hechos del usuario."""

    def test_guardar_y_recuperar(self, m30, store30):
        m30.guardar_hecho(store30, "ana", "nombre", "Ana")
        assert m30.recuperar_hechos(store30, "ana") == {"nombre": "Ana"}

    def test_las_memorias_de_dos_usuarios_no_se_mezclan(self, m30, store30):
        """El aislamiento es la razón de meter el user_id en el namespace."""
        m30.guardar_hecho(store30, "ana", "nombre", "Ana")
        m30.guardar_hecho(store30, "beto", "nombre", "Beto")
        assert m30.recuperar_hechos(store30, "ana") == {"nombre": "Ana"}
        assert m30.recuperar_hechos(store30, "beto") == {"nombre": "Beto"}

    def test_usuario_sin_memorias_devuelve_vacio(self, m30, store30):
        assert m30.recuperar_hechos(store30, "nadie") == {}

    def test_el_namespace_lleva_el_user_id(self, m30):
        assert m30.namespace_de("ana") == ("memorias", "ana")


class TestTema30Extraccion:
    """Decidir QUÉ vale la pena recordar (determinista → testeable)."""

    def test_nombre(self, m30):
        assert m30.extraer_preferencia("hola, me llamo Ana") == ("nombre", "Ana")

    def test_alergia(self, m30):
        assert m30.extraer_preferencia("soy alérgica al maní") == ("alergia", "maní")

    def test_estilo(self, m30):
        assert m30.extraer_preferencia("prefiero respuestas cortas") == ("estilo", "cortas")

    def test_ciudad(self, m30):
        assert m30.extraer_preferencia("vivo en Lima") == ("ciudad", "Lima")

    def test_frase_sin_hecho_no_guarda_ruido(self, m30):
        """No todo turno aporta un hecho: devolver None es la respuesta correcta."""
        assert m30.extraer_preferencia("¿qué tal el clima?") is None


class TestTema30MemoriaEntreHilos:
    """El punto del módulo: el store sobrevive al cambio de thread_id."""

    def test_lo_aprendido_en_un_hilo_se_recupera_en_otro(self, m30, store30):
        # "Conversación 1": el usuario se presenta.
        for frase in ["me llamo Ana", "vivo en Lima", "soy alérgica al maní"]:
            pref = m30.extraer_preferencia(frase)
            if pref:
                m30.guardar_hecho(store30, "ana", *pref)
        # "Conversación 2" (otro thread_id): el mismo store recuerda todo.
        recuerdo = m30.recuperar_hechos(store30, "ana")
        assert recuerdo == {"nombre": "Ana", "ciudad": "Lima", "alergia": "maní"}


# ==================================================================
# TEMA 22b · Voz: audio de entrada (STT) y síntesis (TTS) — offline
# ==================================================================
@pytest.fixture(scope="module")
def m22b(importar_ejemplo):
    return importar_ejemplo("22b_voz")


class TestTema22bVoz:
    """Armar las peticiones de voz (comprensión de audio y TTS) sin llamar a la API."""

    def test_audio_a_bloque_lleva_mime_y_base64(self, m22b):
        import base64
        bloque = m22b.audio_a_bloque(b"RIFF....WAVE", "audio/wav")
        assert bloque["type"] == "media"
        assert bloque["mime_type"] == "audio/wav"
        assert base64.b64decode(bloque["data"]) == b"RIFF....WAVE"

    def test_mensaje_con_audio_tiene_texto_y_audio(self, m22b):
        msg = m22b.mensaje_con_audio("transcribe esto", b"RIFF....WAVE")
        assert len(msg.content) == 2
        assert msg.content[0]["type"] == "text"
        assert msg.content[1]["type"] == "media"

    def test_peticion_tts_arma_el_payload(self, m22b):
        pet = m22b.peticion_tts("hola", "verse", "mp3")
        assert pet == {"input": "hola", "voice": "verse", "format": "mp3"}

    def test_tts_rechaza_voz_desconocida(self, m22b):
        with pytest.raises(ValueError):
            m22b.peticion_tts("x", "inexistente")

    # --- Tiempo real: pipeline STT→LLM→TTS por streaming (offline, determinista) ---
    def test_dividir_en_frases_corta_por_puntuacion(self, m22b):
        frases = list(m22b._dividir_en_frases("Hola. ¿Qué tal? Todo bien"))
        assert frases == ["Hola.", "¿Qué tal?", "Todo bien"]

    def test_pipeline_emite_eventos_en_orden(self, m22b):
        fragmentos = ["a", "b", "c"]
        responder = lambda _t: iter(["uno ", "dos."])
        tipos = [tipo for tipo, _ in m22b.pipeline_voz_streaming(fragmentos, responder)]
        # STT parcial ×3 → final_stt → token ×2 → audio ×1 (una sola frase)
        assert tipos == ["parcial", "parcial", "parcial", "final_stt", "token", "token", "audio"]

    def test_pipeline_transcribe_incremental_y_completo(self, m22b):
        eventos = list(m22b.pipeline_voz_streaming(["¿Cuál ", "horario?"], lambda _t: iter([])))
        parciales = [dato for tipo, dato in eventos if tipo == "parcial"]
        assert parciales == ["¿Cuál ", "¿Cuál horario?"]          # la transcripción crece trozo a trozo
        assert [dato for tipo, dato in eventos if tipo == "final_stt"] == ["¿Cuál horario?"]

    def test_pipeline_sintetiza_una_frase_por_evento_audio(self, m22b):
        responder = lambda _t: iter(["Sí. ", "Claro."])          # dos frases
        audios = [dato for tipo, dato in m22b.pipeline_voz_streaming(["x"], responder) if tipo == "audio"]
        assert [a["input"] for a in audios] == ["Sí.", "Claro."]  # una síntesis por frase completa
        assert all(a["voice"] == "verse" for a in audios)         # y con el payload TTS bien armado
