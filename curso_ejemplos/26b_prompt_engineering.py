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

  Este ejemplo INVOCA AL MODELO DE VERDAD: ves few-shot ganándole a zero-shot en
  el caso del desempate, CoT razonando un cálculo de varios pasos, y —el corazón
  del módulo— MIDES cuánto sube el acierto de few-shot vs zero-shot sobre un
  mini-dataset, llamando al modelo en cada caso. Medir es lo que separa el prompt
  engineering de la superstición: no se ajusta a ojo, se ajusta y se comprueba.

  ⚠️ CADA CORRIDA CONSUME CUOTA. El número que mide [4] no es determinista: con
     6 reseñas y un modelo que varía, puede bailar entre corridas. Aquí aprendes
     la FORMA de medir; medir EN SERIO es un dataset grande y la tríada RAG del
     TEMA 16c, no seis casos a mano.

  Mención a DSPy (solo lectura, NO se instala): en vez de que TÚ afines el prompt
  a mano, DSPy trata el prompt como parámetros a OPTIMIZAR contra una métrica y
  un set de ejemplos —prompt engineering hecho búsqueda automática, no artesanía.

LÓGICA (paso a paso):
  1) Cargamos la llave y creamos el modelo (uno a T=0, otro a T=0.8).
  2) Few-shot vs zero-shot en la reseña que exige el desempate de la casa.
  3) CoT vs directo en un cálculo de varios pasos.
  4) Self-consistency: 5 pasadas a T=0.8 sobre una trampa, votando la moda.
  5) Medir de verdad: exact-match de few-shot vs zero-shot sobre el mini-dataset.

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con tu llave
Ejecuta:    uv run python 26b_prompt_engineering.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import re                          # extraer números y trocear por conectores
from collections import Counter    # contar votos para la mayoría (self-consistency)

from util import (                 # la fábrica del curso: modelo, llave y errores de cuota
    cargar_var_entorno,
    crear_llm,
    es_error_cuota,
    mensaje_cuota,
    requiere_llm_key,
)


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
# Separadores que SIEMPRE marcan un paso nuevo: no son ambiguos en español.
_SEPARADORES_FUERTES = re.compile(
    r"\s*(?:;|,|\by luego\b|\by después\b|\bluego\b|\bdespués\b)\s*"
)

# ⚠️ LA "y" A SECAS ES AMBIGUA, y aquí está la trampa del troceo por reglas. En
#    español la "y" une pasos ("revisa el stock y calcula el total") pero también
#    une sustantivos ("camisas y pantalones"). Partir por toda "y" produce basura:
#    de "revisa el stock de camisas y pantalones" salía un paso llamado
#    "pantalones", que no es ninguna tarea.
#
#    Regla: la "y" solo separa cuando lo que viene DETRÁS empieza por un verbo de
#    acción. Es una heurística, no gramática — y por eso se declara la lista.
_VERBOS_DE_ACCION = (
    "busca", "calcula", "suma", "resta", "revisa", "valida", "verifica",
    "descarga", "resume", "extrae", "clasifica", "compara", "genera",
    "guarda", "envía", "ordena", "filtra", "cuenta", "actualiza",
)
_Y_ANTES_DE_VERBO = re.compile(
    r"\s+y\s+(?=(?:" + "|".join(_VERBOS_DE_ACCION) + r")\b)", re.IGNORECASE
)


def descomponer(tarea: str) -> list[str]:
    """Parte una tarea compuesta en la lista de sub-pasos que la forman.

    POR QUÉ: un prompt que pide TRES cosas a la vez ("busca el precio y calcula
    el IVA y suma el total") invita al modelo a atajar u olvidar un paso. Si lo
    partes y resuelves cada sub-pregunta por separado, cada una es más simple y
    verificable.

    CÓMO: primero por los separadores inequívocos (";", ",", "luego", "después")
    y después por la "y" —pero solo la que va seguida de un verbo de acción, ver
    el comentario de arriba—.

    ⚠️ LÍMITE HONESTO: esto es una heurística de juguete, útil para ver la idea
    sin gastar un token. En un caso real la descomposición NO se hace con
    expresiones regulares: la propone el propio modelo (o una plantilla fija por
    tipo de tarea), justamente porque el lenguaje natural no se deja trocear con
    una lista de conectores.
    """
    partes: list[str] = []
    for bloque in _SEPARADORES_FUERTES.split(tarea):
        if not bloque or not bloque.strip():
            continue
        partes.extend(p.strip() for p in _Y_ANTES_DE_VERBO.split(bloque) if p.strip())
    return partes


# ==================================================================
# 5) EL CASO DEL MÓDULO · clasificar reseñas en la taxonomía de la casa
# ==================================================================
# La misma taxonomía interna de resenas.csv (m03). El desempate de la casa
# —"si hay defecto de producto Y mala atención, manda el DEFECTO"— es lo que
# few-shot enseña en una línea y una instrucción a secas describe mal.
CATEGORIAS = ("LOGISTICA", "PRODUCTO", "ATENCION", "APP")

INSTRUCCION_CLASIFICAR = (
    "Clasifica la reseña en UNA de estas categorías: "
    "LOGISTICA, PRODUCTO, ATENCION, APP. "
    "Responde SOLO con la categoría en mayúsculas."
)

# Las 4 demostraciones del few-shot. La 3ª vale por un párrafo: habla de producto
# Y de atención, y la casa decide que manda el DEFECTO.
EJEMPLOS_FEWSHOT = [
    ("Llegó dos días antes de lo prometido y bien embalado.", "LOGISTICA"),
    ("La app se cierra sola cada vez que intento pagar con Yape.", "APP"),
    ("Excelente atención en la tienda, me explicaron todo con paciencia.", "ATENCION"),
    ("Vino rayado y encima nadie contesta el correo.", "PRODUCTO"),
]

# Mini-dataset con label de oro para MEDIR. Incluye dos casos de desempate
# (defecto + mala atención → PRODUCTO), justo donde zero-shot suele fallar.
DATASET_RESENAS = [
    {"reseña": "Tardó tres semanas en llegar, pero el vendedor me fue avisando.", "categoria": "LOGISTICA"},
    {"reseña": "El vaso vino rajado y además nadie responde mis correos.", "categoria": "PRODUCTO"},
    {"reseña": "No puedo iniciar sesión en la app desde la última actualización.", "categoria": "APP"},
    {"reseña": "La chica del mostrador fue amabilísima y resolvió todo al toque.", "categoria": "ATENCION"},
    {"reseña": "Me llegó el modelo equivocado y encima me colgaron el teléfono.", "categoria": "PRODUCTO"},
    {"reseña": "El paquete se perdió en el courier y llevo cinco días esperando.", "categoria": "LOGISTICA"},
]


def _prompt_zero_shot(reseña: str) -> str:
    """Solo la instrucción y la reseña. Sin demostraciones (k = 0)."""
    return f"{INSTRUCCION_CLASIFICAR}\n\nReseña: {reseña}"


def _prompt_few_shot(reseña: str) -> str:
    """La MISMA instrucción + k demostraciones que enseñan la taxonomía y el desempate.

    La única diferencia con `_prompt_zero_shot` son las demos: así, si el acierto
    sube, sabemos que lo movieron ELLAS y no otra cosa (cambiar una sola variable).
    """
    return f"{INSTRUCCION_CLASIFICAR}\n\n{construir_prompt_fewshot(EJEMPLOS_FEWSHOT, reseña)}"


def _extraer_categoria(respuesta: str) -> str:
    """La primera categoría válida que aparezca en la respuesta del modelo.

    El modelo puede envolver la etiqueta en texto ("La categoría es PRODUCTO.").
    Nos quedamos con la primera de CATEGORIAS que aparezca; si ninguna, "".
    """
    texto = respuesta.upper()
    for categoria in CATEGORIAS:
        if categoria in texto:
            return categoria
    return ""


def _medir(llm, construir_prompt_fn, dataset: list[dict]) -> float:
    """Exactitud (exact-match) de una estrategia LLAMANDO al modelo caso por caso.

    Es el eco REAL del harness offline anterior: la métrica es la misma
    (fracción de aciertos), pero ahora la respuesta la da el modelo, no un
    resolutor determinista. Por eso el número puede variar entre corridas.
    """
    if not dataset:
        return 0.0
    aciertos = 0
    for caso in dataset:
        respuesta = llm.invoke(construir_prompt_fn(caso["reseña"])).text
        if _extraer_categoria(respuesta) == caso["categoria"]:
            aciertos += 1
    return aciertos / len(dataset)


# ==================================================================
# main() · las cuatro técnicas, ejecutadas contra el modelo real
# ==================================================================
def main() -> None:
    # El guard va DENTRO de main(): el archivo se importa (y testea) sin llave.
    cargar_var_entorno()
    if (error := requiere_llm_key()) is not None:
        raise SystemExit(error)

    llm = crear_llm(temperature=0.0)           # tareas deterministas: few-shot, CoT, medir
    llm_creativo = crear_llm(temperature=0.8)   # self-consistency necesita variar entre pasadas

    print("=" * 66)
    print("PROMPT ENGINEERING · cuatro técnicas, contra el modelo real")
    print("=" * 66)

    try:
        # --- [1] Few-shot vs zero-shot en el caso que exige el desempate ---
        reseña = "El vaso vino rajado y además nadie responde mis correos."
        print("\n[1] FEW-SHOT vs ZERO-SHOT · reseña con producto Y atención:")
        print(f'    "{reseña}"')
        print("    (esperado: PRODUCTO — en esta casa manda el DEFECTO)\n")
        zs = _extraer_categoria(llm.invoke(_prompt_zero_shot(reseña)).text)
        fs = _extraer_categoria(llm.invoke(_prompt_few_shot(reseña)).text)
        print(f"    zero-shot (solo instrucción)      → {zs or '¿?'}")
        print(f"    few-shot  (4 demos con desempate)  → {fs or '¿?'}")
        print("    → la 3ª demo enseña el desempate en una línea; describirlo cuesta un párrafo.")

        # --- [2] Chain-of-thought vs respuesta directa ---
        pregunta = ("Un cliente devuelve 3 polos de S/ 45 cada uno. La tienda "
                    "descuenta 10% de penalidad sobre el total devuelto. "
                    "¿Cuánto se le reembolsa?")
        print("\n[2] CHAIN-OF-THOUGHT vs DIRECTO · un cálculo de varios pasos:")
        print(f"    {pregunta}")
        print("    (esperado: 121.50 → 3 × 45 = 135, menos 10%)\n")
        directo = llm.invoke(f"{pregunta}\n\nResponde SOLO con el número.").text.strip()
        con_cot = llm.invoke(plantilla_cot(pregunta)).text.strip()
        print(f"    directo → {directo[:80]}")
        print(f"    con CoT → …{con_cot[-90:].strip()}")
        print("    → escribir los pasos evita el salto directo a una conclusión equivocada.")

        # --- [3] Self-consistency: votar la moda de N pasadas a temperatura>0 ---
        trampa = ("Un almacén tiene 17 cajas. Todas menos 9 se despachan. "
                  "¿Cuántas quedan? Responde SOLO con el número.")
        print("\n[3] SELF-CONSISTENCY · 5 pasadas a temperatura 0.8 sobre una trampa:")
        print(f"    {trampa}")
        print("    (esperado: 9 — 'todas menos 9' es la trampa; el 8 = 17−9 es el error típico)\n")
        muestras: list[str] = []
        descartadas = 0
        for _ in range(5):
            # `.text` saca el texto plano aunque venga en content_blocks.
            respuesta = llm_creativo.invoke(plantilla_cot(trampa)).text.strip()
            nums = re.findall(r"-?\d+", respuesta)
            if nums:
                muestras.append(nums[-1])   # el número final es lo que se vota
            else:
                # Una pasada sin número NO es un voto: ensuciaría la moda.
                descartadas += 1
        print(f"    muestras: {muestras}"
              + (f"  ({descartadas} sin número, descartadas)" if descartadas else ""))
        print(f"    → mayoría (moda): {self_consistency(muestras)}")
        print("      una sola pasada puede caer en la trampa; la moda de 5 la filtra.")

        # --- [4] MEDIR de verdad: ¿cuánto sube el acierto few-shot vs zero-shot? ---
        print("\n[4] MEDIR LA MEJORA · exact-match sobre el mini-dataset, LLAMANDO al modelo:")
        acc_zero = _medir(llm, _prompt_zero_shot, DATASET_RESENAS)
        acc_few = _medir(llm, _prompt_few_shot, DATASET_RESENAS)
        print(f"    zero-shot: {acc_zero:.0%}")
        print(f"    few-shot : {acc_few:.0%}")
        print(f"    → la mejora medida son {(acc_few - acc_zero) * 100:.0f} puntos sobre "
              f"{len(DATASET_RESENAS)} reseñas.")
        print("      ⚠️ Son 6 casos y el modelo no es determinista: el número puede bailar")
        print("      entre corridas. Esto es la FORMA de medir, no el veredicto — medir")
        print("      EN SERIO es un dataset grande y la tríada RAG del c16c.")
    except Exception as error:  # noqa: BLE001
        if es_error_cuota(error):
            print(mensaje_cuota())
            return
        raise


if __name__ == "__main__":
    main()
