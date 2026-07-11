"""
cost_model.py · De tokens a dólares
====================================
FINALIDAD:
  Traducir el consumo de una llamada (tokens de entrada y de salida) al número
  que le importa a quien paga la factura. "El asistente funciona bien" es una
  frase incompleta hasta saber si funciona bien a un coste soportable.

  ⭐ La asimetría a interiorizar: los tokens de SALIDA cuestan varias veces más
     que los de entrada. Consecuencia contraintuitiva: meter el catálogo en el
     contexto NO es lo caro; lo caro es una respuesta larga.

⚠️ LA TABLA CADUCA. Es una foto de julio de 2026 (la misma que usa
   proyecto_llmops); los proveedores cambian precios y retiran modelos. Trátala
   como orden de magnitud y contrástala con la web del proveedor antes de
   presupuestar nada. Un modelo desconocido cuesta 0.0 y no revienta: un informe
   de costes no debe tumbar el servicio que estaba midiendo.
"""
from __future__ import annotations

from dataclasses import dataclass

# Dólares por 1.000.000 de tokens. Foto de 2026-07 (espejo de proyecto_llmops).
PRECIOS: dict[str, dict[str, float]] = {
    #  modelo                        entrada   salida
    "qwen/qwen3-32b":            {"entrada": 0.29, "salida": 0.59},
    "llama-3.3-70b-versatile":   {"entrada": 0.59, "salida": 0.79},
    "gemini-3.1-flash-lite":     {"entrada": 0.25, "salida": 1.50},
    "gemini-2.5-flash":          {"entrada": 0.30, "salida": 2.50},
    "qwen3:8b":                  {"entrada": 0.0, "salida": 0.0},
}


@dataclass(frozen=True)
class Uso:
    """Los tokens que consumió UNA llamada al modelo."""
    entrada: int = 0
    salida: int = 0

    @property
    def total(self) -> int:
        return self.entrada + self.salida


def extraer_uso(mensaje) -> Uso:
    """Saca el consumo de una respuesta de LangChain, sea del proveedor que sea.

    LangChain normaliza el consumo de todos los proveedores en `usage_metadata`.
    Devuelve ceros si el proveedor no lo informó (pasa en streaming): un 0 aquí
    significa "no sé", no "fue gratis".
    """
    uso = getattr(mensaje, "usage_metadata", None) or {}
    return Uso(entrada=uso.get("input_tokens", 0), salida=uso.get("output_tokens", 0))


def precio_de(modelo: str) -> dict[str, float] | None:
    """El precio del modelo, o None si no está en la tabla."""
    return PRECIOS.get(modelo)


def estimar_costo(uso: Uso, modelo: str) -> float:
    """Coste en dólares de una llamada. FUNCIÓN PURA. Los precios son 'por millón'."""
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
    """El número que se lleva a una reunión de presupuesto: coste × tráfico × 30."""
    return costo_por_request * requests_por_dia * 30
