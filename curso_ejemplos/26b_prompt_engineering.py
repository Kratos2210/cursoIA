"""
TEMA 26b · Prompt engineering como disciplina (no como superstición)
====================================================================
FINALIDAD:
  "Prompt engineering" suena a trucos sueltos ("dile que es un experto", "ponle
  POR FAVOR en mayúsculas"). No lo es. Es un puñado de TÉCNICAS con nombre,
  motivo y —lo importante— una forma de MEDIR si ayudan. Este módulo enseña
  cuatro que se sostienen con evidencia y las conecta con lo que ya sabes:

    1) FEW-SHOT (demostración): en vez de describir la tarea, la MUESTRAS con k
       ejemplos resueltos antes de la pregunta real. El modelo imita el patrón.
    2) CHAIN-OF-THOUGHT (CoT): le pides que razone paso a paso ANTES de dar la
       respuesta. Para tareas con pasos intermedios (aritmética, lógica), pensar
       en voz alta reduce el salto directo a una conclusión equivocada.
    3) SELF-CONSISTENCY: muestreas VARIAS respuestas con temperatura>0 y te
       quedas con la de MAYORÍA (la moda). Una sola pasada puede tropezar por
       azar; la moda de N pasadas cancela ese ruido aleatorio.
    4) DESCOMPOSICIÓN: partes una tarea grande en sub-preguntas más simples y
       resuelves cada una. Divide y vencerás, aplicado al prompt.

  ⭐ 100% OFFLINE en su LÓGICA medible. Las cuatro técnicas se implementan como
     FUNCIONES PURAS de texto (sin red, sin API, sin llave) para que se puedan
     testear byte a byte. Además hay un harness "antes/después" con un mini
     solver DETERMINISTA que demuestra —sin gastar un token— que estructurar la
     tarea (CoT/descomposición) sube el acierto. Es el eco offline de medir con
     evals de verdad: eso se hace "en serio" en el TEMA 16 con la tríada RAG.

  La parte ONLINE es opcional: si hay LLM_PROVIDER + llave, main() enseña
  self-consistency REAL muestreando el mismo prompt varias veces a temperatura>0
  con util.crear_llm(). Sin llave, main() corre igual la comparación offline.

  Mención a DSPy (solo lectura, NO se instala): en vez de que TÚ afines el prompt
  a mano, DSPy trata el prompt como parámetros a OPTIMIZAR contra una métrica y
  un set de ejemplos —prompt engineering hecho búsqueda automática, no artesanía.

LÓGICA (paso a paso):
  1) construir_prompt_fewshot(): k demostraciones + la pregunta, en orden.
  2) plantilla_cot(): añade la estructura de razonamiento ("paso a paso").
  3) self_consistency(): votación por mayoría sobre varias respuestas (moda).
  4) descomponer(): parte una tarea en sub-preguntas por sus conectores.
  5) resolver_directo() / resolver_cot() + evaluar(): el harness antes/después.

Requisitos: ninguno extra (solo Python).  La parte online usa util.crear_llm().
Ejecuta:    uv run python 26b_prompt_engineering.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import re                          # extraer números y trocear por conectores
from collections import Counter    # contar votos para la mayoría (self-consistency)


# ==================================================================
# 1) FEW-SHOT · enseñar con ejemplos, no con instrucciones
# ==================================================================
def construir_prompt_fewshot(ejemplos: list[tuple[str, str]], pregunta: str) -> str:
    """Arma un prompt con k demostraciones (pregunta→respuesta) y luego la pregunta real.

    POR QUÉ funciona: el modelo es un imitador de patrones. Si le MUESTRAS tres
    veces "así se resuelve esto", copiará el formato y el estilo en el cuarto caso
    mucho mejor que si se lo DESCRIBES con palabras. El ORDEN importa —las
    demostraciones van antes, la pregunta al final— porque el modelo continúa el
    texto: lo último que ve es la pregunta sin responder, y su trabajo es cerrarla.
    """
    bloques = [f"P: {p}\nR: {r}" for p, r in ejemplos]
    bloques.append(f"P: {pregunta}\nR:")   # la pregunta real, aún SIN responder
    return "\n\n".join(bloques)


# ==================================================================
# 2) CHAIN-OF-THOUGHT · pedir el razonamiento antes de la respuesta
# ==================================================================
FRASE_COT = "Pensemos paso a paso y expliquemos el razonamiento antes de dar la respuesta final."


def plantilla_cot(pregunta: str) -> str:
    """Envuelve la pregunta con la instrucción de razonar paso a paso.

    POR QUÉ ayuda: en tareas con pasos intermedios (aritmética, lógica de varios
    saltos), forzar al modelo a ESCRIBIR el camino evita que salte directo a una
    conclusión. No es magia: es darle espacio para "pensar en voz alta". ⚠️ CoT
    NO inventa conocimiento —si el modelo no sabe el dato, razonar no lo arregla.
    """
    return f"{pregunta}\n\n{FRASE_COT}"


# ==================================================================
# 3) SELF-CONSISTENCY · votación por mayoría sobre varias muestras
# ==================================================================
def self_consistency(respuestas: list[str]) -> str | None:
    """Devuelve la respuesta de MAYORÍA (la moda) entre varias muestras.

    POR QUÉ: con temperatura>0 el modelo no es determinista; cada muestra puede
    tomar un camino distinto y alguna se equivoca por azar. Si muestreas N veces
    la MISMA pregunta y te quedas con la respuesta más repetida, el ruido
    aleatorio de las pasadas malas se cancela y sube el acierto —el mismo
    principio que promediar varias mediciones ruidosas de un termómetro.

    Determinista y testeable: mayoría clara → esa; empate → la que apareció
    PRIMERO (Counter conserva el orden de inserción); lista vacía → None.
    """
    if not respuestas:
        return None
    conteo = Counter(respuestas)
    tope = max(conteo.values())
    # De las que empatan en el máximo, la primera en aparecer (orden de inserción).
    for respuesta in respuestas:
        if conteo[respuesta] == tope:
            return respuesta
    return None  # inalcanzable, pero deja explícito el contrato


# ==================================================================
# 4) DESCOMPOSICIÓN · partir una tarea grande en sub-preguntas
# ==================================================================
_CONECTORES = re.compile(r"\s*(?:;|,|\by luego\b|\bluego\b|\bdespués\b|\by después\b|\by\b)\s*")


def descomponer(tarea: str) -> list[str]:
    """Parte una tarea compuesta en la lista de sub-pasos que la forman.

    POR QUÉ: un prompt que pide TRES cosas a la vez ("busca el precio y calcula
    el IVA y suma el total") invita al modelo a atajar u olvidar un paso. Si lo
    partes y resuelves cada sub-pregunta por separado, cada una es más simple y
    verificable. Aquí troceamos por los conectores ("y", "luego", ";", …); en un
    caso real la descomposición la propone el propio modelo o una plantilla.
    """
    partes = [p.strip() for p in _CONECTORES.split(tarea) if p and p.strip()]
    return partes


# ==================================================================
# 5) HARNESS "antes/después" · medir que un prompt mejor acierta más
# ==================================================================
# Mini-dataset FIJO y offline: problemas de una operación con su respuesta exacta.
# Cada enunciado tiene exactamente dos números y una palabra que revela la
# operación. Es el "eco" del TEMA 16, donde se mide en serio con la tríada RAG.
DATASET = [
    {"pregunta": "Ana tiene 3 manzanas y compra 2 más. ¿Cuántas tiene ahora?", "respuesta": "5"},
    {"pregunta": "Un bus lleva 12 pasajeros y suben 5. ¿Cuántos van en total?", "respuesta": "17"},
    {"pregunta": "Luis tenía 20 soles y gastó 8. ¿Cuánto le queda?", "respuesta": "12"},
    {"pregunta": "Hay 7 gatos en el patio y llegan 4 más. ¿Cuántos hay?", "respuesta": "11"},
    {"pregunta": "María horneó 15 panes y vendió 9. ¿Cuántos le quedan?", "respuesta": "6"},
]

# Palabras que delatan una RESTA; si no aparece ninguna, asumimos suma.
_PALABRAS_RESTA = ("gastó", "gasta", "vendió", "vende", "perdió", "pierde",
                   "regaló", "regala", "quita", "quitó", "menos", "queda", "quedan")


def _numeros(texto: str) -> list[int]:
    """Los enteros que aparecen en el texto, en orden."""
    return [int(n) for n in re.findall(r"-?\d+", texto)]


def resolver_directo(pregunta: str) -> str:
    """Estrategia POBRE: el modelo apurado agarra el PRIMER número que ve y lo
    suelta como respuesta, sin razonar. Es el 'salto directo a la conclusión'
    que CoT viene a corregir. Casi siempre falla en cuanto hay una operación."""
    nums = _numeros(pregunta)
    return str(nums[0]) if nums else ""


def resolver_cot(pregunta: str) -> str:
    """Estrategia BUENA: descompone el enunciado (¿qué números? ¿qué operación?)
    y RECIÉN calcula. Es CoT/descomposición hechos código determinista: mismo
    espíritu que pedirle al LLM que razone paso a paso antes de responder."""
    nums = _numeros(pregunta)
    if len(nums) < 2:
        return str(nums[0]) if nums else ""
    a, b = nums[0], nums[1]
    es_resta = any(palabra in pregunta.lower() for palabra in _PALABRAS_RESTA)
    return str(a - b if es_resta else a + b)


def evaluar(estrategia, dataset: list[dict]) -> float:
    """Exactitud (exact-match) de una estrategia sobre el dataset: fracción de
    respuestas que coinciden EXACTAMENTE con la esperada. Métrica determinista,
    sin LLM y sin juez: se puede afirmar en un test."""
    if not dataset:
        return 0.0
    aciertos = sum(1 for caso in dataset if estrategia(caso["pregunta"]) == caso["respuesta"])
    return aciertos / len(dataset)


def comparar_estrategias() -> dict[str, float]:
    """El experimento antes/después en una llamada: exactitud de la estrategia
    directa vs la de CoT/descomposición sobre el mismo mini-dataset."""
    return {
        "directo": evaluar(resolver_directo, DATASET),
        "cot": evaluar(resolver_cot, DATASET),
    }


# ==================================================================
# main() · la parte offline SIEMPRE corre; la online es un extra
# ==================================================================
def _demo_offline() -> None:
    """Todo lo que no necesita red: few-shot, CoT, descomposición, el harness
    antes/después y un ejemplo de self-consistency por votación."""
    print("=" * 64)
    print("PROMPT ENGINEERING · demostración 100% OFFLINE")
    print("=" * 64)

    # --- Few-shot: un prompt armado con demostraciones ---
    ejemplos = [
        ("Traduce 'gato' al inglés", "cat"),
        ("Traduce 'perro' al inglés", "dog"),
    ]
    print("\n[1] FEW-SHOT · prompt con 2 demostraciones + la pregunta real:\n")
    print(construir_prompt_fewshot(ejemplos, "Traduce 'casa' al inglés"))

    # --- CoT: la misma pregunta, ahora con estructura de razonamiento ---
    print("\n[2] CHAIN-OF-THOUGHT · la pregunta envuelta para razonar:\n")
    print(plantilla_cot("Si un tren sale a las 9 y tarda 2 horas, ¿a qué hora llega?"))

    # --- Descomposición: una tarea compuesta partida en sub-pasos ---
    tarea = "busca el precio del producto y calcula el IVA y suma el total"
    print("\n[3] DESCOMPOSICIÓN · una tarea grande en sub-preguntas:")
    for i, paso in enumerate(descomponer(tarea), 1):
        print(f"    {i}. {paso}")

    # --- Self-consistency: mayoría sobre varias muestras ruidosas ---
    muestras = ["42", "42", "17", "42", "17"]   # como si vinieran de 5 pasadas
    print(f"\n[4] SELF-CONSISTENCY · 5 muestras {muestras}")
    print(f"    → mayoría (moda): {self_consistency(muestras)}")

    # --- Harness antes/después: el número que justifica todo lo anterior ---
    marcador = comparar_estrategias()
    print("\n[5] MEDIR LA MEJORA · exactitud sobre el mini-dataset (exact-match):")
    print(f"    Prompt POBRE  (salto directo)     : {marcador['directo']:.0%}")
    print(f"    Prompt MEJOR  (CoT/descomposición): {marcador['cot']:.0%}")
    print("    → estructurar la tarea sube el acierto. En el TEMA 16 esto se")
    print("      mide 'en serio' con un dataset y la tríada RAG, no a ojo.")


def _demo_online() -> None:
    """Self-consistency REAL: muestrea la MISMA pregunta N veces a temperatura>0
    y vota. Solo corre si hay proveedor + llave; si no, se salta sin romper."""
    import util

    if util.requiere_llm_key() is not None:
        print("\n(La demo ONLINE de self-consistency se salta: no hay llave. "
              "Todo lo de arriba ya demostró la técnica offline.)")
        return

    print("\n" + "=" * 64)
    print("SELF-CONSISTENCY REAL · muestreo a temperatura>0 (usa cuota)")
    print("=" * 64)
    pregunta = ("Un granjero tiene 17 ovejas. Todas menos 9 se escapan. "
                "¿Cuántas le quedan? Responde SOLO con el número.")
    llm = util.crear_llm(temperature=0.8)   # temperatura>0: cada muestra puede variar
    muestras: list[str] = []
    try:
        for _ in range(5):
            respuesta = llm.invoke(plantilla_cot(pregunta)).content.strip()
            # Nos quedamos con el número final, que es lo que se vota.
            nums = re.findall(r"-?\d+", respuesta)
            muestras.append(nums[-1] if nums else respuesta)
    except Exception as error:  # noqa: BLE001
        if util.es_error_cuota(error):
            print(util.mensaje_cuota())
            return
        raise
    print(f"Muestras de las 5 pasadas: {muestras}")
    print(f"Respuesta por MAYORÍA     : {self_consistency(muestras)}  (esperado: 9)")


def main() -> None:
    _demo_offline()
    _demo_online()


if __name__ == "__main__":
    main()
