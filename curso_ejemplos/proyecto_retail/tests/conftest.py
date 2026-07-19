"""
conftest.py · Los dobles de prueba del asistente de compras retail
===================================================================
FINALIDAD:
  Ejercitar el pipeline completo (intención → búsqueda → redacción → grounding)
  sin llamar a ningún modelo. Todo lo caro entra por parámetro, así que aquí le
  pasamos un doble:

    - ModeloFalso : recita un guion. Para la intención devuelve un FiltrosCompra
                    de guion; para la redacción, un texto de guion (que puede
                    citar un precio inventado, para probar el guardrail).

LÓGICA — por qué un fake y no un mock de librería: el fake implementa EXACTAMENTE
  la interfaz que el código usa (`with_structured_output(...).invoke()` y
  `.invoke(...).content`). Si mintiera sobre la forma, el test pasaría y la app
  fallaría.
"""
from __future__ import annotations

import pytest

from proyecto_retail.app.etl import cargar_catalogo_demo
from proyecto_retail.app.intent import FiltrosCompra


class _Mensaje:
    """Un AIMessage mínimo: el código solo le mira `.content`."""
    def __init__(self, content: str):
        self.content = content


class _EstructuradoFalso:
    """Se hace pasar por `llm.with_structured_output(FiltrosCompra)`."""
    def __init__(self, filtros: list[FiltrosCompra]):
        self._filtros = filtros
        self._i = 0

    def invoke(self, _prompt, *a, **k) -> FiltrosCompra:
        f = self._filtros[min(self._i, len(self._filtros) - 1)]
        self._i += 1
        return f


class ModeloFalso:
    """Un chat model de guion. Cero red, cero cuota.

    filtros    : el/los FiltrosCompra que devuelve `with_structured_output`.
    redacciones: el/los textos que devuelve `invoke().content`. Se van
                 consumiendo en orden (la 1ª para la redacción, la 2ª para el
                 reintento correctivo), y la última se repite si se piden más.
    """
    def __init__(self, filtros: FiltrosCompra | list[FiltrosCompra] | None = None,
                 redacciones: str | list[str] | None = None):
        if isinstance(filtros, FiltrosCompra):
            filtros = [filtros]
        self._filtros = filtros or [FiltrosCompra()]
        if isinstance(redacciones, str):
            redacciones = [redacciones]
        self._redacciones = redacciones or [""]
        self._i = 0
        self.invocaciones: list = []

    def with_structured_output(self, _schema, **_kw):
        return _EstructuradoFalso(self._filtros)

    def invoke(self, mensajes, *a, **k) -> _Mensaje:
        self.invocaciones.append(mensajes)
        texto = self._redacciones[min(self._i, len(self._redacciones) - 1)]
        self._i += 1
        return _Mensaje(texto)


@pytest.fixture
def catalogo() -> list[dict]:
    """El catálogo demo normalizado (12 productos con la forma de Shopify)."""
    return cargar_catalogo_demo()


@pytest.fixture
def modelo_falso():
    """La CLASE ModeloFalso, para que cada test la instancie con su guion."""
    return ModeloFalso
