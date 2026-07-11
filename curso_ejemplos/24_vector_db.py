"""
TEMA 24 · Del vector store en memoria a una DB vectorial de verdad
==================================================================
FINALIDAD:
  Cierra el arco de RAG (TEMA 11/12/20). Hasta ahora el "vector store" era una
  lista en memoria y la búsqueda comparaba la consulta con TODOS los vectores
  (escaneo exacto). Eso funciona con 7 chunks; con 7 millones, no. Dos ideas que
  te separan de un prototipo y te acercan a producción:

    1) DEDUP POR HASH antes de indexar. No metas la misma info dos veces: infla el
       coste (más vectores que guardar y escanear) y SESGA el ranking (un chunk
       repetido tres veces "gana" por multiplicidad, no por relevancia).
    2) ÍNDICE ANN (Approximate Nearest Neighbor). En vez de comparar con todos,
       AGRUPA los vectores en listas alrededor de centroides (IVFFlat) y solo mira
       las listas más cercanas a la consulta. Cambias un poco de recall por MUCHA
       velocidad. Aquí lo implementamos a mano para VER el trade-off.

  ⭐ 100% OFFLINE: no llama a ninguna API ni gasta cuota. Usamos vectores DIDÁCTICOS
     de frecuencia de palabras (los mismos del TEMA 12), no embeddings reales, para
     que la mecánica del índice se vea sin depender de un modelo.

LÓGICA (paso a paso):
  1) vectorizar(): texto -> vector de frecuencias (Counter), como el TEMA 12.
  2) hash_normalizado() + deduplicar(): quitar duplicados exactos y casi-exactos.
  3) construir_ivf(): agrupar los vectores en n_listas alrededor de centroides.
  4) buscar_ivf(): sondar solo las n_sondas listas más cercanas y devolver el top-k.
  5) buscar_exacto(): el techo de recall (compara con todos) para medirnos contra él.

Requisitos: ninguno extra (solo Python).  Este script NO llama a la API.
Ejecuta:    uv run python 24_vector_db.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import hashlib   # sha256 para la huella de cada chunk (dedup)
import math      # 'sqrt' para la similitud coseno
import os        # ruta a datos_rag.txt sin importar desde dónde ejecutes
import re        # tokenizar y normalizar el texto
from collections import Counter        # vector de frecuencias de palabras
from dataclasses import dataclass      # el índice IVF como estructura con nombre


# ============ 0) TEXTO -> VECTOR (didáctico, como el TEMA 12) ============
def cargar_chunks() -> list[str]:
    """Lee datos_rag.txt y lo parte en fragmentos por párrafo (como el TEMA 11/12)."""
    ruta = os.path.join(os.path.dirname(__file__), "datos_rag.txt")
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()
    return [p.strip() for p in contenido.split("\n\n") if p.strip()]


def tokenizar(texto: str) -> list[str]:
    """Minúsculas y separado en palabras. El paso previo de TODO buscador."""
    return re.findall(r"[a-záéíóúüñ0-9\-]+", texto.lower())


def vectorizar(texto: str) -> Counter:
    """Convierte un texto en un vector de frecuencias de palabras.

    Los embeddings reales devuelven un vector denso que captura SIGNIFICADO; aquí,
    igual que en el TEMA 12, usamos el conteo de palabras como sustituto didáctico.
    La mecánica del índice (agrupar y sondar) es idéntica sea cual sea el vector.
    """
    return Counter(tokenizar(texto))


def coseno(a, b) -> float:
    """Similitud coseno entre dos vectores dispersos (dicts palabra -> peso).
    1 = misma dirección, 0 = nada en común. Sirve para Counter y para centroides."""
    comunes = set(a) & set(b)
    producto = sum(a[t] * b[t] for t in comunes)
    norma_a = math.sqrt(sum(v * v for v in a.values()))
    norma_b = math.sqrt(sum(v * v for v in b.values()))
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return producto / (norma_a * norma_b)


# ============ 1) DEDUP POR HASH ============
def hash_normalizado(texto: str) -> str:
    """Huella sha256 del texto NORMALIZADO (minúsculas, sin puntuación, espacios
    colapsados). Dos textos que solo difieren en mayúsculas, comas o dobles espacios
    producen el MISMO hash: así cazamos también los casi-duplicados, no solo los
    idénticos byte a byte.
    """
    normalizado = " ".join(tokenizar(texto))
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


def deduplicar(chunks: list[str]) -> list[str]:
    """Quita duplicados exactos y casi-exactos conservando el ORDEN de aparición.

    POR QUÉ antes de indexar: cada duplicado es un vector más que guardar, embeber y
    escanear (coste), y encima envenena el ranking —tres copias del mismo párrafo se
    reparten los primeros puestos y desplazan información distinta. Nos quedamos con
    la PRIMERA aparición de cada huella.
    """
    vistos: set[str] = set()
    unicos: list[str] = []
    for chunk in chunks:
        huella = hash_normalizado(chunk)
        if huella not in vistos:
            vistos.add(huella)
            unicos.append(chunk)
    return unicos


# ============ 2) ÍNDICE IVFFlat (didáctico) ============
@dataclass
class IndiceIVF:
    """El índice IVFFlat: los centroides, las listas (qué vectores cayeron en cada
    centroide) y los vectores originales para poder puntuarlos al buscar."""
    centroides: list[dict]
    listas: list[list[int]]   # listas[c] = índices de los vectores del centroide c
    vectores: list[Counter]


def _centroide(vectores: list[Counter]) -> dict:
    """El vector medio de un grupo: para cada palabra, su peso promedio. Es el
    'representante' de la lista; la consulta se compara contra él para decidir si
    vale la pena sondar esa lista."""
    if not vectores:
        return {}
    acumulado: Counter = Counter()
    for v in vectores:
        acumulado.update(v)
    return {palabra: total / len(vectores) for palabra, total in acumulado.items()}


def construir_ivf(vectores: list[Counter], n_listas: int, iteraciones: int = 5) -> IndiceIVF:
    """Agrupa los vectores en n_listas listas (k-means didáctico y DETERMINISTA).

    POR QUÉ agrupar: al buscar no querremos comparar la consulta con el millón de
    vectores, sino solo con los de las listas cercanas. Para eso primero hay que
    'entrenar' el índice: repartir los vectores en grupos y calcular su centroide.
    Inicializamos los centroides con vectores repartidos (sin azar, para que el test
    sea reproducible) y afinamos con unas pocas iteraciones de Lloyd.
    """
    n = len(vectores)
    n_listas = max(1, min(n_listas, n))
    # Semillas deterministas: n_listas vectores repartidos a lo largo de la colección.
    paso = max(1, n // n_listas)
    centroides = [dict(vectores[min(i * paso, n - 1)]) for i in range(n_listas)]

    listas: list[list[int]] = [[] for _ in range(n_listas)]
    for _ in range(iteraciones):
        nuevas: list[list[int]] = [[] for _ in range(n_listas)]
        for idx, v in enumerate(vectores):
            # A cada vector, la lista de su centroide MÁS parecido.
            mejor = max(range(n_listas), key=lambda c: coseno(v, centroides[c]))
            nuevas[mejor].append(idx)
        # Recalculamos cada centroide como la media de sus miembros (si quedó vacío,
        # conservamos el anterior para no perder la lista).
        for c in range(n_listas):
            if nuevas[c]:
                centroides[c] = _centroide([vectores[i] for i in nuevas[c]])
        if nuevas == listas:      # convergió: no hace falta seguir iterando
            listas = nuevas
            break
        listas = nuevas
    return IndiceIVF(centroides=centroides, listas=listas, vectores=vectores)


def buscar_ivf(consulta: Counter, indice: IndiceIVF, k: int = 3, n_sondas: int = 1) -> list[int]:
    """Búsqueda aproximada: sondea solo las n_sondas listas cuyo centroide es más
    parecido a la consulta y devuelve los k mejores de ESAS listas.

    El trade-off en una perilla: n_sondas.
      · n_sondas = 1     -> rapidísimo, pero si el vecino cayó en otra lista, lo pierdes.
      · n_sondas = todas -> escaneas todo: mismo recall que el exacto, sin ventaja.
    Subir n_sondas nunca EMPEORA el recall (miras un superconjunto de listas), solo
    cuesta más. Ese es el corazón de un índice ANN: recall a cambio de velocidad.
    """
    n_listas = len(indice.centroides)
    n_sondas = max(1, min(n_sondas, n_listas))
    orden = sorted(range(n_listas), key=lambda c: coseno(consulta, indice.centroides[c]), reverse=True)
    candidatos = [idx for c in orden[:n_sondas] for idx in indice.listas[c]]
    candidatos.sort(key=lambda i: coseno(consulta, indice.vectores[i]), reverse=True)
    return candidatos[:k]


def buscar_exacto(consulta: Counter, vectores: list[Counter], k: int = 3) -> list[int]:
    """El techo de recall: compara la consulta con TODOS los vectores (fuerza bruta).
    Es contra esto que medimos si el índice aproximado 'acierta'."""
    orden = sorted(range(len(vectores)), key=lambda i: coseno(consulta, vectores[i]), reverse=True)
    return orden[:k]


def main() -> None:
    chunks = cargar_chunks()
    # Metemos a mano un CASI-duplicado del chunk de horario: mismo texto pero en
    # MAYÚSCULAS y con dobles espacios. Byte a byte es distinto; tras normalizar, no.
    casi_duplicado = "  " + chunks[2].upper().replace(" ", "  ")
    envenenado = chunks + [casi_duplicado]
    print(f"Chunks cargados: {len(envenenado)} (uno es casi-duplicado del horario).")

    limpios = deduplicar(envenenado)
    print(f"Tras deduplicar por hash: {len(limpios)} (se cayó el casi-duplicado).\n")

    vectores = [vectorizar(c) for c in limpios]
    indice = construir_ivf(vectores, n_listas=3)
    tamanos = [len(l) for l in indice.listas]
    print(f"Índice IVFFlat con {len(indice.centroides)} listas; tamaños: {tamanos}")

    consulta = vectorizar("¿cuál es el horario de atención?")
    exacto = buscar_exacto(consulta, vectores, k=3)
    print(f"\nConsulta: '¿cuál es el horario de atención?'")
    print(f"  Escaneo EXACTO (techo de recall): top-3 = {exacto}")
    for sondas in (1, 2, 3):
        aprox = buscar_ivf(consulta, indice, k=3, n_sondas=sondas)
        recall = len(set(aprox) & set(exacto)) / len(exacto)
        print(f"  IVF n_sondas={sondas}: top-3 = {aprox}  · recall vs exacto = {recall:.2f}")

    print("\n💡 En producción no escribes esto a mano: lo dan pgvector (Postgres),")
    print("   Qdrant o Milvus, que ofrecen IVFFlat y HNSW como tipos de índice. El")
    print("   proyecto_llmops ya vectoriza en local; el salto a una DB vectorial es")
    print("   cambiar el 'vector store en memoria' por uno de esos, MISMA interfaz de RAG.")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        print("❌ No encuentro datos_rag.txt (debe estar junto a este script).")
    except Exception as error:
        print(f"❌ Error inesperado: {error}")
