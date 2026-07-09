"""
TEMA 12 · RAG en profundidad: búsqueda híbrida + re-ranking
==========================================================
FINALIDAD:
  Entender POR DENTRO las dos técnicas que más mejoran un RAG de producción:
    a) Búsqueda HÍBRIDA: combinar búsqueda por palabras clave (BM25) con
       búsqueda por "significado" (similitud de vectores).
    b) Fusión de rankings (RRF) y RE-RANKING: reordenar los candidatos para
       que el mejor fragmento quede arriba antes de dárselo al modelo.

  ⭐ Este ejemplo es 100% OFFLINE: no llama a ninguna API ni gasta cuota.
     Implementamos las fórmulas a mano (en pequeño) para que veas la mecánica
     que librerías como `rank_bm25` o los re-rankers hacen en grande.

LÓGICA (paso a paso):
  1) Cargamos datos_rag.txt y lo troceamos en fragmentos (chunks).
  2) BUSCADOR 1 — BM25: puntúa por coincidencia de palabras exactas.
  3) BUSCADOR 2 — vectorial (versión didáctica): cada texto se convierte en
     un vector de frecuencias y se compara con similitud coseno. Los
     embeddings reales (gemini-embedding-001) son la versión "con esteroides"
     de esta misma idea: vectores que además capturan el significado.
  4) FUSIÓN RRF: combina ambos rankings sin pelear con escalas distintas.
  5) RE-RANKING: un segundo filtro más exigente reordena los finalistas.
  6) Comparamos los rankings para VER por qué el híbrido gana.

Requisitos: ninguno extra (solo Python).  Este script NO llama a la API.
Ejecuta:    uv run python curso_ejemplos/12_rag_hibrido_rerank.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import math      # 'log' para la fórmula BM25 y 'sqrt' para la similitud coseno
import os        # construir la ruta al archivo de datos sin importar desde dónde ejecutes
import re        # separar el texto en palabras (tokenizar) con una expresión regular
from collections import Counter   # contar cuántas veces aparece cada palabra


# ============ 1) CARGAR Y TROCEAR EL DOCUMENTO ============
def cargar_chunks() -> list[str]:
    """Lee datos_rag.txt y lo parte en fragmentos por párrafo (como el TEMA 11)."""
    ruta = os.path.join(os.path.dirname(__file__), "datos_rag.txt")
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()
    # Un chunk por párrafo: simple y suficiente para este documento pequeño.
    return [p.strip() for p in contenido.split("\n\n") if p.strip()]


def tokenizar(texto: str) -> list[str]:
    """Pasa a minúsculas y separa en palabras. Es el paso previo de TODO buscador."""
    return re.findall(r"[a-záéíóúüñ0-9\-]+", texto.lower())


# ============ 2) BUSCADOR POR PALABRAS: BM25 ============
# BM25 es el algoritmo clásico de los buscadores (lo usa Elasticsearch).
# Idea: un chunk puntúa alto si contiene las palabras EXACTAS de la pregunta,
# dando más valor a palabras raras (ej. "ISO-27001") que a comunes (ej. "datos").
def puntuar_bm25(pregunta: str, chunks: list[str], k1=1.5, b=0.75) -> list[float]:
    docs = [tokenizar(c) for c in chunks]
    n_docs = len(docs)
    largo_promedio = sum(len(d) for d in docs) / n_docs

    # ¿En cuántos documentos aparece cada palabra? (para saber cuáles son "raras")
    doc_freq = Counter()
    for d in docs:
        for palabra in set(d):
            doc_freq[palabra] += 1

    puntajes = []
    for d in docs:
        frecuencias = Counter(d)
        puntaje = 0.0
        for palabra in tokenizar(pregunta):
            if palabra not in frecuencias:
                continue                       # esta palabra no está en el chunk
            # IDF: cuanto más RARA es la palabra en el corpus, más puntos vale
            idf = math.log(1 + (n_docs - doc_freq[palabra] + 0.5) / (doc_freq[palabra] + 0.5))
            # TF saturado: que repetir 50 veces una palabra no dispare el puntaje
            tf = frecuencias[palabra] * (k1 + 1) / (
                frecuencias[palabra] + k1 * (1 - b + b * len(d) / largo_promedio)
            )
            puntaje += idf * tf
        puntajes.append(puntaje)
    return puntajes


# ============ 3) BUSCADOR "VECTORIAL" (didáctico) ============
# Convertimos cada texto en un VECTOR (aquí: conteo de palabras) y medimos el
# ángulo entre vectores (similitud coseno). Los embeddings de verdad hacen esto
# mismo pero con vectores que capturan SIGNIFICADO (perro ≈ can) y no solo letras.
def similitud_coseno(a: Counter, b: Counter) -> float:
    comunes = set(a) & set(b)
    producto_punto = sum(a[p] * b[p] for p in comunes)
    norma_a = math.sqrt(sum(v * v for v in a.values()))
    norma_b = math.sqrt(sum(v * v for v in b.values()))
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return producto_punto / (norma_a * norma_b)


def puntuar_vectorial(pregunta: str, chunks: list[str]) -> list[float]:
    vector_pregunta = Counter(tokenizar(pregunta))
    return [similitud_coseno(vector_pregunta, Counter(tokenizar(c))) for c in chunks]


# ============ 4) FUSIÓN DE RANKINGS: RRF ============
# Problema: BM25 devuelve puntajes tipo 7.3 y el vectorial tipo 0.42.
# No se pueden sumar directo. RRF (Reciprocal Rank Fusion) ignora los puntajes
# y usa el PUESTO: estar 1º en cualquier lista vale 1/(60+1), estar 2º vale
# 1/(60+2), etc. Quien queda bien parado en AMBAS listas, gana.
def fusionar_rrf(*rankings: list[int], k: int = 60) -> list[int]:
    puntajes: dict[int, float] = {}
    for ranking in rankings:                     # cada ranking = índices ordenados
        for puesto, idx in enumerate(ranking):
            puntajes[idx] = puntajes.get(idx, 0.0) + 1.0 / (k + puesto + 1)
    return sorted(puntajes, key=lambda idx: puntajes[idx], reverse=True)


# ============ 5) RE-RANKING (segundo filtro, más exigente) ============
# Un cross-encoder real lee pregunta+chunk JUNTOS y da un puntaje fino (lento
# pero certero). Aquí lo simulamos con una señal más exigente que la búsqueda:
# ¿qué proporción de las palabras de la pregunta aparecen en el chunk, con
# bono si aparecen SEGUIDAS (como frase)? Suficiente para ver el efecto.
def re_rankear(pregunta: str, chunks: list[str], candidatos: list[int], top_n=3) -> list[int]:
    palabras = [p for p in tokenizar(pregunta) if len(p) > 3]   # ignora "de", "la"...
    puntuados = []
    for idx in candidatos:
        texto = chunks[idx].lower()
        cobertura = sum(1 for p in palabras if p in texto) / max(len(palabras), 1)
        bono_frase = 0.5 if " ".join(palabras[:2]) in texto else 0.0
        puntuados.append((cobertura + bono_frase, idx))
    puntuados.sort(reverse=True)                  # mejor puntaje arriba
    return [idx for _, idx in puntuados[:top_n]]  # solo los top_n finalistas


# ---------- utilidades de presentación ----------
def ordenar(puntajes: list[float]) -> list[int]:
    """Convierte una lista de puntajes en un ranking de índices (mejor primero)."""
    return sorted(range(len(puntajes)), key=lambda i: puntajes[i], reverse=True)


def mostrar(titulo: str, ranking: list[int], chunks: list[str], n=3):
    print(f"\n=== {titulo} ===")
    for puesto, idx in enumerate(ranking[:n], start=1):
        resumen = chunks[idx].replace("\n", " ")[:90]
        print(f"  {puesto}º · chunk {idx}: {resumen}…")


def main():
    chunks = cargar_chunks()
    print(f"Documento troceado en {len(chunks)} chunks (uno por párrafo).")

    # Una pregunta con término "exacto" (donde BM25 brilla) y significado (donde
    # lo vectorial ayuda). Cambia la pregunta y observa cómo cambian los rankings.
    pregunta = "¿Cuál es el horario de atención de soporte?"
    print(f"\nPregunta: {pregunta}")

    # ---- Cada buscador por separado ----
    ranking_bm25 = ordenar(puntuar_bm25(pregunta, chunks))
    ranking_vect = ordenar(puntuar_vectorial(pregunta, chunks))
    mostrar("Ranking 1 · BM25 (palabras exactas)", ranking_bm25, chunks)
    mostrar("Ranking 2 · Vectorial (similitud coseno)", ranking_vect, chunks)

    # ---- Fusión híbrida ----
    hibrido = fusionar_rrf(ranking_bm25, ranking_vect)
    mostrar("Ranking 3 · HÍBRIDO (fusión RRF)", hibrido, chunks)

    # ---- Re-ranking de los 5 mejores candidatos ----
    finalistas = re_rankear(pregunta, chunks, candidatos=hibrido[:5], top_n=3)
    mostrar("Ranking 4 · RE-RANKEADO (los 3 finalistas)", finalistas, chunks)

    print("\n💡 En producción: BM25 -> rank_bm25/BM25Retriever · vectorial -> ")
    print("   embeddings reales + Chroma · re-ranker -> cross-encoder (BAAI/bge-reranker).")
    print("   El contexto que le pasarías al LLM son ESOS 3 finalistas, no 20 candidatos.")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        print("❌ No encuentro datos_rag.txt (debe estar junto a este script).")
    except Exception as error:
        print(f"❌ Error inesperado: {error}")
