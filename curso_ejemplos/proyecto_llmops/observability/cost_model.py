"""
cost_model.py · De tokens a dólares
====================================
FINALIDAD:
  Traducir el consumo de una llamada (tokens de entrada y de salida) al número
  que le importa a quien paga la factura. Sin esto, "el agente funciona bien" es
  una frase incompleta: falta saber si funciona bien a un coste soportable.

  ⭐ La asimetría que hay que interiorizar: **los tokens de SALIDA cuestan varias
     veces más que los de entrada**. Consecuencia contraintuitiva: un RAG que
     mete 4.000 tokens de contexto NO es lo caro. Lo caro es una respuesta larga.
     Optimizar el prompt para ahorrar suele ser optimizar el sitio equivocado.

LÓGICA:
  - PRECIOS: la tabla, en dólares por MILLÓN de tokens.
  - extraer_uso(mensaje): saca el consumo de una respuesta de LangChain.
  - estimar_costo(uso, modelo): la multiplicación.
  - formatear_costo(dolares): para que $0.000018 se lea.

⚠️ LA TABLA CADUCA. Es una foto de julio de 2026, no una verdad eterna: los
   proveedores cambian precios y retiran modelos. Trátala como un orden de
   magnitud y contrástala con la web del proveedor antes de presupuestar nada.
   Por eso `estimar_costo` de un modelo desconocido devuelve 0.0 y no revienta:
   un informe de costes no debe tumbar el servicio que estaba midiendo.
"""
from __future__ import annotations

from dataclasses import dataclass

# Dólares por 1.000.000 de tokens. Foto de 2026-07.
#
# Fíjate en la columna 'salida': entre 2x y 8x la de entrada, según el modelo.
PRECIOS: dict[str, dict[str, float]] = {
    #  modelo                        entrada   salida
    # --- Groq (el default del .env.example) ---
    "qwen/qwen3-32b":            {"entrada": 0.29, "salida": 0.59},
    "llama-3.3-70b-versatile":   {"entrada": 0.59, "salida": 0.79},
    # --- Google (el resto del curso) ---
    "gemini-3.1-flash-lite":     {"entrada": 0.25, "salida": 1.50},
    "gemini-2.5-flash":          {"entrada": 0.30, "salida": 2.50},
    # Apagado el 2026-06-01. Se queda para que los costes históricos que ya
    # tengas registrados sigan calculándose con la tarifa que se cobró.
    "gemini-2.0-flash":          {"entrada": 0.10, "salida": 0.40},
    # --- Local: no cuesta dinero, cuesta tu electricidad y tu RAM ---
    "qwen3:8b":                  {"entrada": 0.0, "salida": 0.0},
}


@dataclass(frozen=True)
class Uso:
    """Los tokens que consumió UNA llamada al modelo.

    Se separa de `MetricasRequest` (metrics.py) a propósito: el uso es un hecho
    del proveedor; la métrica es lo que nosotros decidimos observar de él.
    """
    entrada: int = 0
    salida: int = 0

    @property
    def total(self) -> int:
        return self.entrada + self.salida


def extraer_uso(mensaje) -> Uso:
    """Saca el consumo de una respuesta de LangChain, sea del proveedor que sea.

    ⭐ LangChain normaliza el consumo de TODOS los proveedores en
       `usage_metadata`. El campo crudo de cada uno vive en `response_metadata`,
       pero ahí Groq lo llama de una forma y Google de otra. No te ates a él.

    Devuelve ceros si el proveedor no informó del consumo. Pasa de verdad: en
    **streaming**, muchos proveedores no mandan el conteo hasta el último chunk,
    y algunos no lo mandan nunca. Un 0 aquí significa "no sé", no "fue gratis".
    """
    uso = getattr(mensaje, "usage_metadata", None) or {}
    return Uso(
        entrada=uso.get("input_tokens", 0),
        salida=uso.get("output_tokens", 0),
    )


class ContadorDeUso:
    """Suma el consumo de UNA request que hizo VARIAS llamadas al modelo.

    Existe por el streaming. `extraer_uso` lee el consumo de un mensaje suelto,
    pero en streaming el modelo no devuelve un mensaje: devuelve una lluvia de
    chunks, y el conteo llega —cuando llega— en el último. Peor: un ciclo ReAct
    hace varias llamadas (decidir tool → leer resultado → redactar), así que hay
    varios conteos que sumar, no uno que leer.

    Se le empujan todos los fragmentos del stream y al final se le pide `.uso`.
    Un total en 0 sigue significando "el proveedor no lo informó", nunca "gratis".
    """

    def __init__(self) -> None:
        self._entrada = 0
        self._salida = 0

    def sumar(self, fragmento) -> None:
        """Acumula el consumo del fragmento, si es que lo trae. Ignora los que no."""
        uso = extraer_uso(fragmento)
        self._entrada += uso.entrada
        self._salida += uso.salida

    @property
    def uso(self) -> Uso:
        return Uso(entrada=self._entrada, salida=self._salida)


def precio_de(modelo: str) -> dict[str, float] | None:
    """El precio del modelo, o None si no está en la tabla."""
    return PRECIOS.get(modelo)


def estimar_costo(uso: Uso, modelo: str) -> float:
    """Coste en dólares de una llamada. FUNCIÓN PURA.

    Los precios son 'por millón', de ahí el 1_000_000. Un modelo desconocido
    cuesta 0.0: preferimos subestimar el gasto a caernos al reportarlo.
    (El aviso de que el modelo no está en la tabla lo da `metrics.py`.)
    """
    precio = precio_de(modelo)
    if precio is None:
        return 0.0
    return (uso.entrada * precio["entrada"] + uso.salida * precio["salida"]) / 1_000_000


def formatear_costo(dolares: float) -> str:
    """Un coste de $0.000018 no se lee de un vistazo. Lo mostramos en su escala."""
    if dolares == 0:
        return "$0 (sin datos de consumo)"
    if dolares < 0.01:
        return f"${dolares:.6f}"
    return f"${dolares:.4f}"


def proyectar_mensual(costo_por_request: float, requests_por_dia: int) -> float:
    """El número que de verdad se lleva a una reunión de presupuesto.

    $0.0002 por request no asusta a nadie. $0.0002 × 50.000 requests/día × 30
    días = $300/mes, y eso ya es una conversación. La diferencia entre las dos
    cifras es la razón por la que existe este archivo.
    """
    return costo_por_request * requests_por_dia * 30
