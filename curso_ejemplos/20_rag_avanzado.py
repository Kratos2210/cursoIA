"""
TEMA 20 · RAG avanzado: transformar la PREGUNTA antes de buscar
================================================================
FINALIDAD:
  El TEMA 12 mejoró el RAG por el lado del ÍNDICE: buscar mejor (híbrido) y
  reordenar mejor (re-ranking) DESPUÉS de recuperar. Aquí atacamos el otro
  extremo: la PREGUNTA. Una sola formulación deja huecos ("devolución" no
  encuentra "reembolso"). La cura es preguntar de VARIAS maneras y fusionar
  lo que traiga cada una.

    a) MULTI-QUERY: a partir de tu pregunta generamos 3–4 reformulaciones
       (sinónimos, sin muletillas, solo palabras clave).
    b) RAG-FUSION: recuperamos con cada reformulación y fusionamos los
       rankings con RRF (la misma fórmula del TEMA 12). Un chunk que aparece
       en VARIAS búsquedas sube; el ruido de una sola se diluye.

  ⭐ Este ejemplo es 100% OFFLINE: no llama a ninguna API ni gasta cuota.
     Implementamos la mecánica a mano. En producción, quien genera las
     reformulaciones es el LLM (con `util.crear_llm()`), no unas plantillas.

LÓGICA (paso a paso):
  1) Cargamos datos_rag.txt y lo troceamos en fragmentos (chunks).
  2) expandir_consulta(): reescribe la pregunta de varias formas deterministas.
  3) recuperar(): para cada reformulación, top-k por similitud (coseno didáctico).
  4) fusion_rrf(): fusiona todos esos rankings en uno solo.
  5) rag_fusion(): orquesta expandir -> recuperar -> fusionar.
  6) comprimir_contexto(): recorta el contexto a las frases que de verdad tocan.

Requisitos: ninguno extra (solo Python).  Este script NO llama a la API.
Ejecuta:    uv run python 20_rag_avanzado.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import math      # 'sqrt' para la similitud coseno
import os        # construir la ruta al archivo de datos sin importar desde dónde ejecutes
import re        # separar el texto en palabras (tokenizar) y en frases
from collections import Counter   # contar cuántas veces aparece cada palabra


# ============ 0) DATOS Y TOKENIZADO (igual que el TEMA 11/12) ============
def cargar_chunks() -> list[str]:
    """Lee datos_rag.txt y lo parte en fragmentos por párrafo."""
    ruta = os.path.join(os.path.dirname(__file__), "datos_rag.txt")
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()
    return [p.strip() for p in contenido.split("\n\n") if p.strip()]


def tokenizar(texto: str) -> list[str]:
    """Pasa a minúsculas y separa en palabras. El paso previo de TODO buscador."""
    return re.findall(r"[a-záéíóúüñ0-9\-]+", texto.lower())


# Muletillas que no aportan a la búsqueda: al quitarlas, la reformulación
# "solo palabras clave" se concentra en lo que de verdad discrimina un chunk.
STOPWORDS = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "mi", "tu", "su",
    "y", "o", "a", "en", "que", "es", "por", "para", "del", "al", "se", "con",
    "cómo", "como", "cuál", "cuales", "cuánto", "cuanto", "puedo", "pido", "quiero",
}

# El corazón del multi-query OFFLINE: un mapa de sinónimos del dominio. Es lo que
# tapa el hueco clásico "devolución" (lo que dice el usuario) ↔ "reembolso" (lo que
# dice el documento). El LLM real conoce miles de estos pares; aquí bastan unos pocos.
SINONIMOS = {
    "devolución": "reembolso", "devolucion": "reembolso", "devoluciones": "reembolso",
    "reintegro": "reembolso", "reintegros": "reembolso",
    "pagar": "pago", "cuotas": "pago", "abonar": "pago",
    "soporte": "atención", "atencion": "atención", "ayuda": "atención",
    "horario": "atención", "credenciales": "llaves", "contraseña": "llaves",
}


# ============ 1) MULTI-QUERY: expandir la pregunta ============
def expandir_consulta(pregunta: str) -> list[str]:
    """Genera varias reformulaciones deterministas de la pregunta.

    POR QUÉ: una sola formulación es una sola apuesta. Si el usuario dijo
    "devolución" y el documento dice "reembolso", esa apuesta pierde. Con 3–4
    variantes (sinónimos, sin muletillas, solo clave) tapamos ese hueco.

    En producción esto lo hace el LLM: `crear_llm().invoke("dame 3 formas de
    preguntar lo mismo: ...")`. Aquí, plantillas deterministas para que el test
    sea reproducible y no gaste cuota.
    """
    base = pregunta.strip()
    tokens = tokenizar(base)
    variantes = [base]

    # 2) Solo palabras clave: fuera muletillas.
    clave = [t for t in tokens if t not in STOPWORDS]
    if clave:
        variantes.append(" ".join(clave))

    # 3) Sustituir cada palabra por su sinónimo del dominio (si lo tiene).
    sustituida = [SINONIMOS.get(t, t) for t in tokens]
    variantes.append(" ".join(sustituida))

    # 4) La pregunta original MÁS los sinónimos añadidos al final (no reemplaza,
    #    suma señales): así una búsqueda cubre ambos vocabularios a la vez.
    extra = list(dict.fromkeys(SINONIMOS[t] for t in tokens if t in SINONIMOS))
    if extra:
        variantes.append(base + " " + " ".join(extra))

    # Quitamos duplicados conservando el orden (dos reformulaciones podrían coincidir).
    return list(dict.fromkeys(variantes))


# ============ 2) RECUPERAR: similitud coseno didáctica (como el TEMA 12) ============
def similitud_coseno(a: Counter, b: Counter) -> float:
    """El ángulo entre dos vectores de conteo de palabras. 1 = idénticos, 0 = nada en común."""
    comunes = set(a) & set(b)
    producto_punto = sum(a[p] * b[p] for p in comunes)
    norma_a = math.sqrt(sum(v * v for v in a.values()))
    norma_b = math.sqrt(sum(v * v for v in b.values()))
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return producto_punto / (norma_a * norma_b)


def terminos(texto: str) -> list[str]:
    """Los tokens que DISCRIMINAN: como tokenizar, pero sin muletillas.

    POR QUÉ quitar stopwords antes de vectorizar: si dejamos 'de', 'la', 'mi'…
    en los vectores, el chunk más corto gana por compartir palabras vacías, no
    por ser relevante. Sin ellas, la similitud mide contenido, no ruido.
    """
    return [t for t in tokenizar(texto) if t not in STOPWORDS]


def puntuar(pregunta: str, chunks: list[str]) -> list[float]:
    """Un puntaje de similitud por chunk frente a la pregunta (sobre términos de contenido)."""
    vector_pregunta = Counter(terminos(pregunta))
    return [similitud_coseno(vector_pregunta, Counter(terminos(c))) for c in chunks]


def recuperar(pregunta: str, chunks: list[str], k: int = 3) -> list[int]:
    """Devuelve los índices de los k chunks más parecidos a la pregunta (mejor primero).

    Descartamos los de puntaje 0 (un umbral mínimo de relevancia): si una
    reformulación no casa con NADA, devuelve una lista vacía en vez de un orden
    arbitrario por índice. Esto es clave para RAG-Fusion: una variante que no
    encontró nada NO debe ensuciar la fusión con ruido ordenado.
    """
    puntajes = puntuar(pregunta, chunks)
    orden = sorted(range(len(chunks)), key=lambda i: puntajes[i], reverse=True)
    return [i for i in orden if puntajes[i] > 0][:k]


# ============ 3) FUSIÓN DE RANKINGS: RRF (idéntico al TEMA 12) ============
def fusion_rrf(rankings: list[list[int]], k: int = 60) -> list[int]:
    """Reciprocal Rank Fusion: fusiona varios rankings usando el PUESTO, no el puntaje.

    Estar 1º en cualquier lista vale 1/(k+1), 2º vale 1/(k+2)... Un chunk que
    aparece bien parado en VARIAS reformulaciones acumula y gana. El que solo una
    búsqueda amó, se queda corto: RRF castiga la ausencia en las demás listas.
    """
    puntajes: dict[int, float] = {}
    for ranking in rankings:
        for puesto, idx in enumerate(ranking):
            puntajes[idx] = puntajes.get(idx, 0.0) + 1.0 / (k + puesto + 1)
    return sorted(puntajes, key=lambda idx: puntajes[idx], reverse=True)


# ============ 4) RAG-FUSION: orquesta todo ============
def rag_fusion(pregunta: str, chunks: list[str], k: int = 3, ancho: int = 3) -> list[int]:
    """Expande la pregunta, recupera con cada variante y fusiona los rankings.

    'ancho' es cuántos candidatos trae cada reformulación (recuperar barato y
    ancho); 'k' es cuántos finalistas devolvemos tras fusionar.
    """
    variantes = expandir_consulta(pregunta)
    rankings = [recuperar(v, chunks, k=ancho) for v in variantes]
    return fusion_rrf(rankings)[:k]


# ============ 5) COMPRESIÓN EXTRACTIVA (opcional) ============
def comprimir_contexto(chunks: list[str], indices: list[int], pregunta: str) -> str:
    """De los chunks elegidos, conserva solo las FRASES que tocan la pregunta.

    POR QUÉ: menos ruido en el contexto = menos tokens y menos alucinación. Es la
    versión a mano de un 'contextual compression retriever'. Incluimos también los
    sinónimos del dominio para no descartar la frase que usa la palabra del documento.
    """
    terminos = {t for t in tokenizar(pregunta) if t not in STOPWORDS and len(t) > 3}
    terminos |= {SINONIMOS[t] for t in tokenizar(pregunta) if t in SINONIMOS}
    frases: list[str] = []
    for idx in indices:
        for frase in re.split(r"(?<=[.:!?])\s+", chunks[idx]):
            if set(tokenizar(frase)) & terminos:
                frases.append(frase.strip())
    return "\n".join(frases)


# ---------- utilidades de presentación ----------
def mostrar(titulo: str, ranking: list[int], chunks: list[str], n: int = 3) -> None:
    print(f"\n=== {titulo} ===")
    if not ranking:
        print("  (nada superó el umbral de relevancia: la pregunta cruda no casó con ningún chunk)")
        return
    for puesto, idx in enumerate(ranking[:n], start=1):
        resumen = chunks[idx].replace("\n", " ")[:90]
        print(f"  {puesto}º · chunk {idx}: {resumen}…")


def main() -> None:
    chunks = cargar_chunks()
    print(f"Documento troceado en {len(chunks)} chunks (uno por párrafo).")

    # La pregunta usa el vocabulario del USUARIO ("devolución de mi dinero"),
    # mientras que el documento usa el de la EMPRESA ("Política de reembolsos").
    pregunta = "¿Cómo pido la devolución de mi dinero?"
    print(f"\nPregunta: {pregunta}")

    # ---- Una sola búsqueda (lo que hace el RAG básico) ----
    solo = recuperar(pregunta, chunks, k=3)
    mostrar("Ranking A · UNA sola búsqueda (pregunta cruda)", solo, chunks)

    # ---- Multi-query: las reformulaciones ----
    variantes = expandir_consulta(pregunta)
    print("\n=== Reformulaciones (multi-query) ===")
    for i, v in enumerate(variantes, start=1):
        print(f"  {i}. {v}")

    # ---- RAG-Fusion: recuperar con cada una y fusionar ----
    fusion = rag_fusion(pregunta, chunks, k=3)
    mostrar("Ranking B · RAG-FUSION (multi-query + RRF)", fusion, chunks)

    # ---- Contexto comprimido: solo las frases que tocan ----
    print("\n=== Contexto comprimido (lo que le pasarías al LLM) ===")
    print(comprimir_contexto(chunks, fusion[:2], pregunta) or "  (sin frases que casen)")

    print("\n💡 En producción: las reformulaciones las escribe el LLM (crear_llm()),")
    print("   la recuperación usa embeddings reales + un vector store, y RRF fusiona")
    print("   igual que aquí. El multi-query brilla cuando la pregunta y el documento")
    print("   usan palabras distintas para la misma idea.")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        print("❌ No encuentro datos_rag.txt (debe estar junto a este script).")
    except Exception as error:
        print(f"❌ Error inesperado: {error}")
