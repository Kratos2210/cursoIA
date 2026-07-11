"""
TEMA 09 · Resiliencia + async (apps que no se caen)
==========================================================
FINALIDAD:
  Que la app siga funcionando si un modelo falla (fallback), reintente
  ante errores temporales (retry) y procese muchas cosas a la vez (async).

LÓGICA (paso a paso):
  1) Ponemos un modelo principal INVÁLIDO a propósito + un respaldo válido.
  2) with_fallbacks hace que la cadena salte sola al respaldo.
  3) with_retry reintenta ante errores temporales (ej. 429).
  4) Con async lanzamos varias preguntas en paralelo.

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/09_resiliencia_async.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import os                                   # variables de entorno
import asyncio                              # 'asyncio': ejecutar tareas en paralelo (async)
from dotenv import load_dotenv              # cargar .env
from util import mensaje_cuota, crear_llm, requiere_llm_key   # el modelo, del proveedor que diga el .env
from langchain_core.prompts import ChatPromptTemplate       # plantillas de prompt
from langchain_core.output_parsers import StrOutputParser   # respuesta -> texto plano


def main():
    # ---- 1) Preparar llave ------------------------------
    load_dotenv()
    if (error := requiere_llm_key()):
        raise SystemExit(error)

    # ---- 2) Fallback: principal (falla) + respaldo ------
    # El principal tiene un nombre inválido para VER el salto al respaldo.
    # `modelo=` fuerza ese nombre; el respaldo usa el modelo por defecto de tu
    # proveedor (gemini-3.1-flash-lite con Google, qwen/qwen3-32b con Groq).
    principal = crear_llm(temperature=0, modelo="modelo-que-no-existe")
    respaldo = crear_llm(temperature=0)
    modelo_robusto = principal.with_fallbacks([respaldo])

    # ---- 3) retry: reintenta ante errores temporales ----
    prompt = ChatPromptTemplate.from_template("Responde en una frase: {q}")
    cadena = (prompt | modelo_robusto | StrOutputParser()).with_retry(stop_after_attempt=3)

    print("=== Fallback en acción (el principal falla, responde el respaldo) ===")
    print(cadena.invoke({"q": "¿Qué es la resiliencia en software?"}), "\n")

    # ---- 4) async: varias preguntas a la vez ------------
    async def procesar_todo(preguntas):
        tareas = [cadena.ainvoke({"q": q}) for q in preguntas]  # 'a' delante = versión async
        return await asyncio.gather(*tareas)                    # espera a que terminen todas

    print("=== async: 3 preguntas en paralelo ===")
    preguntas = ["¿Qué es un fallback?", "¿Qué es un timeout?", "¿Qué es la latencia?"]
    respuestas = asyncio.run(procesar_todo(preguntas))          # arranca el bucle async
    for q, r in zip(preguntas, respuestas):
        print(f"- {q}\n  {r}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print(mensaje_cuota())   # el mensaje depende del proveedor activo
        else:
            print(f"❌ Error inesperado: {error}")
