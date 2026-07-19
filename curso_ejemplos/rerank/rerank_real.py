"""
PROFUNDIDAD · El re-ranker DE VERDAD (cross-encoder ONNX) vs el didáctico
=========================================================================
FINALIDAD:
  El m12 implementó el re-ranking A MANO —cobertura de palabras + bono de frase—
  para que la MECÁNICA se viera sin instalar nada (ADR-0002). Funciona para
  enseñar, pero tiene el fallo que el propio m12 confiesa: si ninguna palabra de
  la pregunta aparece en el chunk, puntúa 0.0 a todos y el orden es ARBITRARIO.

  Este companion pone el re-ranker real al lado del didáctico, sobre el MISMO
  corpus y la MISMA pregunta, para que veas la diferencia con tus ojos:

      recuperar (rápido, tonto)  ->  re-rankear (lento, listo)
                                     didáctico:  ¿comparten palabras?
                                     REAL:       ¿este texto RESPONDE la pregunta?

  ⭐ Un cross-encoder lee pregunta y chunk JUNTOS y puntúa la relevancia. Por eso
     entiende sinónimos ("devolución" ~ "reembolso") donde el didáctico ve 0.0.

  ⭐ FUERA DEL GATE OFFLINE (ver docs/adr/0008): descarga un modelo (~80 MB) la
     primera vez. NO se testea en la CI. Reutiliza el extra `emb` que ya existe.

  ⭐ POR QUÉ fastembed y no `HuggingFaceCrossEncoder`: el snippet del m12 usa la
     vía HuggingFace, que arrastra PyTorch — y PyTorch NO tiene wheels para macOS
     Intel (ver el extra `hf` en pyproject.toml). fastembed corre el MISMO tipo de
     modelo sobre ONNX Runtime: sin torch, ~80 MB, y funciona en cualquier
     plataforma del curso. Mismo concepto, otra caja.

Ejecuta:  uv run --extra emb python rerank/rerank_real.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

# Reutilizamos el corpus y el re-ranker didáctico del m12 (sin duplicarlos). El
# archivo empieza por dígito, así que se carga por ruta —igual que el fixture
# `importar_ejemplo` de los tests y que el anexo de voz.
_ruta_m12 = Path(__file__).resolve().parent.parent / "12_rag_hibrido_rerank.py"
_spec = importlib.util.spec_from_file_location("rerank_m12", _ruta_m12)
_m12 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m12)

# El modelo. VERIFICA los ids disponibles con:
#   TextCrossEncoder.list_supported_models()
# El multilingüe entiende español; los `ms-marco` son solo inglés y más rápidos.
MODELO_RERANK = "jinaai/jina-reranker-v2-base-multilingual"


def re_rankear_real(pregunta: str, chunks: list[str], candidatos: list[int],
                    top_n: int = 3) -> list[tuple[float, int]]:
    """Re-rankea los candidatos con un cross-encoder real. Devuelve (puntaje, idx).

    Devolvemos el PUNTAJE y no solo el orden a propósito: es la lección del m12
    ("un ranking sin puntajes es una opinión disfrazada de dato"). Con el puntaje,
    quien llama puede decir "todos por debajo del umbral: no tengo respuesta".

    ⚠️ OJO con la escala: estos puntajes son *logits*, no probabilidades de 0 a 1
    (verás valores negativos). Lo que importa es la DISTANCIA entre el primero y
    el resto, no el signo. El umbral de "no tengo respuesta" se calibra por modelo
    con tus propias preguntas —no lo copies de otro proyecto.
    """
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    encoder = TextCrossEncoder(model_name=MODELO_RERANK)
    textos = [chunks[i] for i in candidatos]
    # rerank() lee la pregunta JUNTO a cada texto y devuelve un puntaje por texto.
    puntajes = list(encoder.rerank(pregunta, textos))
    puntuados = sorted(zip(puntajes, candidatos), reverse=True)
    return puntuados[:top_n]


def main() -> None:
    chunks = _m12.cargar_chunks()
    candidatos = list(range(len(chunks)))        # aquí "recuperamos" todo el corpus

    # Una pregunta con CERO palabras en común con el texto: el caso exacto que
    # rompe al didáctico. El manual dice "Política de reembolsos"; el cliente
    # pregunta "¿me devuelven la plata?". Ni una palabra casa (cobertura 0.00),
    # pero cualquier humano sabe cuál es el chunk correcto. Y el cross-encoder
    # también, porque entiende que "devolver la plata" ES un reembolso.
    pregunta = "¿Me devuelven la plata si no me gusta?"

    print(f"❓ {pregunta}\n")

    print("── Re-ranker DIDÁCTICO (m12: cobertura de palabras) ──")
    for puesto, idx in enumerate(_m12.re_rankear(pregunta, chunks, candidatos), 1):
        print(f"  {puesto}. [chunk {idx}] {chunks[idx][:70]}…")
    print("  ⚠️  Si ninguna palabra casa, todos puntúan 0.0 y el orden es arbitrario.\n")

    print(f"── Re-ranker REAL (cross-encoder {MODELO_RERANK}) ──")
    for puesto, (puntaje, idx) in enumerate(re_rankear_real(pregunta, chunks, candidatos), 1):
        print(f"  {puesto}. [{puntaje:+.3f}] [chunk {idx}] {chunks[idx][:70]}…")
    print("  ✅ Puntúa si el texto RESPONDE, no si comparte palabras.")


if __name__ == "__main__":
    main()
