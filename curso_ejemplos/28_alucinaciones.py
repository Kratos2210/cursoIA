"""
TEMA 28 · Desafíos: alucinaciones y por qué fallan los LLM
==========================================================
FINALIDAD:
  Un LLM puede afirmar con total aplomo algo que es falso: eso es una
  ALUCINACIÓN. No es un bug que se "arregla" de una vez —es una consecuencia de
  cómo funciona el modelo (m27: predice el siguiente token, no consulta la
  verdad)—. Lo que SÍ se puede es entender de dónde vienen y montar defensas.
  Este módulo es INTEGRADOR: cada desafío se conecta con la mitigación que el
  curso YA te enseñó, y añade dos detectores nuevos, 100% offline y medibles:

    1) TAXONOMIA — un mapa consultable «causa de alucinación → cómo se detecta
       → con qué mitigación → en qué módulo del curso». Cuelga del marco de los
       cuatro grandes desafíos (datos, ético/social, técnico, despliegue) de la
       teoría, y profundiza la rama técnica: la alucinación.
    2) detectar_inconsistencia() — detector estilo SelfCheckGPT hecho a mano:
       muestrea N veces la MISMA pregunta y mide cuánto DISCREPAN las respuestas.
       Si el modelo SABE el dato, las muestras coinciden; si lo está inventando,
       divergen. La dispersión es la señal de alerta. Es el REVERSO del
       self-consistency del m26b: allí se VOTA la moda para acertar más; aquí se
       MIDE la dispersión para desconfiar.
    3) medir_fragilidad() — misma pregunta con variaciones triviales (una coma,
       un sinónimo): si la respuesta cambia, el resultado es FRÁGIL —dependía de
       la forma del prompt, no del conocimiento—.

  ⭐ 100% OFFLINE. Todo son FUNCIONES PURAS sobre listas de texto (sin red, sin
     API, sin llave). Las "muestras del modelo" se simulan como listas de strings
     para que el detector se pueda testear byte a byte. La idea del filtro de
     perplejidad (m27) reaparece en el HTML como defensa de entrada.

LÓGICA (paso a paso):
  1) TAXONOMIA + causas_por_modulo(): el mapa desafío→mitigación→módulo.
  2) detectar_inconsistencia(): score de divergencia entre muestras (SelfCheckGPT).
  3) medir_fragilidad(): cuántas respuestas distintas ante variaciones triviales.

Requisitos: ninguno extra (solo Python).  No usa red.
Ejecuta:    uv run python 28_alucinaciones.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import re                          # normalizar texto antes de comparar
from collections import Counter    # contar respuestas repetidas (moda)


# ==================================================================
# 1) TAXONOMÍA · de la causa a la mitigación que el curso ya enseñó
# ==================================================================
# Las CATEGORÍAS son los cuatro grandes desafíos de la teoría; aquí abrimos la
# rama que más muerde en producción —la técnica: la alucinación— y mapeamos cada
# causa a la defensa concreta y al módulo donde la practicaste.
TAXONOMIA = [
    {
        "causa": "Datos desactualizados",
        "categoria": "datos",
        "senal": "Afirma hechos que ya cambiaron (precios, cargos, versiones).",
        "mitigacion": "RAG con una fuente fresca: que responda desde el documento, no de memoria.",
        "modulo": "m11",
    },
    {
        "causa": "Falta de grounding",
        "categoria": "datos",
        "senal": "Inventa una cita, un número o una fuente que no existe.",
        "mitigacion": "Grounding con RAG y pedir que cite el fragmento recuperado.",
        "modulo": "m11",
    },
    {
        "causa": "Contexto insuficiente o ambiguo",
        "categoria": "tecnica",
        "senal": "Rellena los huecos de una pregunta vaga con suposiciones.",
        "mitigacion": "Descomponer la tarea y dar contexto explícito en el prompt.",
        "modulo": "m26b",
    },
    {
        "causa": "Sobregeneralización de patrones",
        "categoria": "tecnica",
        "senal": "Da una respuesta plausible pero distinta cada vez que la repites.",
        "mitigacion": "Self-consistency (votar la moda de N muestras) y verificación.",
        "modulo": "m26b",
    },
    {
        "causa": "Sin verificación de la salida",
        "categoria": "tecnica",
        "senal": "Nadie mide si la respuesta es correcta; el error pasa silencioso.",
        "mitigacion": "Evaluar con un dataset y una métrica (la tríada RAG).",
        "modulo": "m16",
    },
    {
        "causa": "Entrada adversarial o envenenada",
        "categoria": "despliegue",
        "senal": "Un prompt o un documento recuperado empuja al modelo a mentir.",
        "mitigacion": "Guardarraíles en capas: detectar, separar datos de instrucciones, sanear.",
        "modulo": "m23",
    },
]

# Las cuatro categorías-paraguas de la teoría (para validar y para el HTML).
CATEGORIAS = ("datos", "etica", "tecnica", "despliegue")


def causas_por_modulo(modulo: str) -> list[str]:
    """Las causas de alucinación que se mitigan en un módulo dado del curso.

    Útil para responder "¿qué problemas resuelve el m11?" desde los datos, sin
    prosa: el mapa es consultable, no un párrafo que se desactualiza.
    """
    return [fila["causa"] for fila in TAXONOMIA if fila["modulo"] == modulo]


def modulos_de_mitigacion() -> set[str]:
    """El conjunto de módulos del curso a los que apunta la taxonomía."""
    return {fila["modulo"] for fila in TAXONOMIA}


# ==================================================================
# 2) DETECTAR INCONSISTENCIA · el reverso del self-consistency (m26b)
# ==================================================================
def _normalizar(texto: str) -> str:
    """Minúsculas, sin puntuación de borde y con espacios colapsados.

    Así "París.", " parís " y "Paris" cuentan como la MISMA respuesta: comparamos
    contenido, no maquetación. Sin esto, un punto final inflaría la divergencia.
    """
    limpio = texto.lower().strip()
    limpio = re.sub(r"[.,;:!?¡¿'\"]", "", limpio)
    return re.sub(r"\s+", " ", limpio)


def detectar_inconsistencia(respuestas: list[str]) -> float:
    """Score de divergencia en [0, 1) entre varias RESPUESTAS a la MISMA pregunta.

    Recibe las respuestas CORTAS ya extraídas (el dato final: "París", "1812"),
    igual que el self_consistency del m26b vota sobre el número extraído. Un
    SelfCheckGPT real compara texto libre por similitud semántica; esta versión
    didáctica compara la respuesta normalizada, que basta para verse en un test.

    POR QUÉ funciona: si el modelo SABE el dato, muestrear la misma pregunta
    varias veces da (casi) siempre la misma respuesta; si lo está INVENTANDO, cada
    muestra fabrica algo distinto. Medimos la dispersión:

        score = 1 - (frecuencia de la respuesta más común / número de muestras)

    0.0  = todas coinciden (consistente, probablemente sabe).
    →1   = todas distintas (alta divergencia, sospecha de alucinación).

    Determinista y testeable: es pura aritmética sobre las cadenas normalizadas.
    """
    if not respuestas:
        return 0.0
    normalizadas = [_normalizar(r) for r in respuestas]
    mas_comun = Counter(normalizadas).most_common(1)[0][1]
    return 1 - mas_comun / len(normalizadas)


def es_sospechosa(respuestas: list[str], umbral: float = 0.5) -> bool:
    """True si la divergencia entre muestras supera el umbral (por defecto 0.5).

    Es el gatillo que un sistema real usaría para NO devolver la respuesta a
    ciegas: pedir una fuente, avisar "no estoy seguro" o escalar a un humano.
    """
    return detectar_inconsistencia(respuestas) >= umbral


# ==================================================================
# 3) MEDIR FRAGILIDAD · ¿la respuesta depende de cómo preguntes?
# ==================================================================
def medir_fragilidad(respuestas_por_variante: list[str]) -> int:
    """Cuántas respuestas DISTINTAS produjeron variaciones triviales del prompt.

    POR QUÉ importa: si cambiar una coma o un sinónimo cambia la respuesta, el
    resultado dependía de la FORMA del prompt, no del conocimiento —es frágil y no
    te puedes fiar—. 1 = robusto (siempre lo mismo); >1 = frágil.
    """
    return len({_normalizar(r) for r in respuestas_por_variante})


def es_fragil(respuestas_por_variante: list[str]) -> bool:
    """True si variaciones triviales del prompt dieron más de una respuesta."""
    return medir_fragilidad(respuestas_por_variante) > 1


# ==================================================================
# main() · demostración 100% OFFLINE (no toca la red)
# ==================================================================
def main() -> None:
    print("=" * 64)
    print("DESAFÍOS Y ALUCINACIONES · demostración 100% OFFLINE")
    print("=" * 64)

    # --- La taxonomía como mapa consultable ---
    print("\n[1] TAXONOMÍA · causa → mitigación → módulo del curso:")
    for fila in TAXONOMIA:
        print(f"    · {fila['causa']:<32} → {fila['mitigacion'][:38]}…  [{fila['modulo']}]")
    print(f"    Módulos que ya te dieron la defensa: {sorted(modulos_de_mitigacion())}")

    # --- Detector de inconsistencia: sabe vs inventa (respuestas cortas extraídas) ---
    sabe = ["París", "parís", "París."]                 # 3 muestras, mismo dato
    inventa = ["1812", "1798", "1820", "1805"]           # 4 muestras, todas distintas
    print("\n[2] DETECTAR INCONSISTENCIA (estilo SelfCheckGPT) · divergencia entre muestras:")
    print(f"    modelo que SABE     {sabe}")
    print(f"       → divergencia {detectar_inconsistencia(sabe):.2f}  · ¿sospechosa? {es_sospechosa(sabe)}")
    print(f"    modelo que INVENTA  {inventa}")
    print(f"       → divergencia {detectar_inconsistencia(inventa):.2f}  · ¿sospechosa? {es_sospechosa(inventa)}")

    # --- Fragilidad de prompts: misma pregunta, variaciones triviales ---
    robusto = ["4", " 4 ", "4."]                         # misma respuesta, distinta forma
    fragil = ["Sí, es seguro", "No, evítalo", "Depende del caso"]
    print("\n[3] MEDIR FRAGILIDAD · respuestas distintas ante variaciones triviales:")
    print(f"    prompt robusto {robusto} → {medir_fragilidad(robusto)} respuesta(s) · ¿frágil? {es_fragil(robusto)}")
    print(f"    prompt frágil  {fragil} → {medir_fragilidad(fragil)} respuesta(s) · ¿frágil? {es_fragil(fragil)}")

    print("\n→ La alucinación no se 'apaga': se detecta (divergencia), se mide")
    print("  (fragilidad) y se mitiga con lo que ya sabes (RAG, evals, guardrails).")


if __name__ == "__main__":
    main()
