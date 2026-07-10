"""
_proyecto_final.py · El puente al prototipo
============================================
FINALIDAD:
  `proyecto_final/` no es un paquete instalable: son scripts sueltos (así lo
  quiere el curso, y por eso el pyproject lleva `[tool.uv] package = false`).
  Para importarlo hay que meter su carpeta en `sys.path`.

  Eso es un truco. Los trucos se hacen UNA vez, en un sitio con nombre, y se
  explican. No se esparcen por seis módulos.

LÓGICA:
  - Bajo pytest esto sobra: el `pythonpath` del pyproject ya incluye
    `proyecto_final`. Pero uvicorn y `python -m app.main` no leen esa config.
  - `_asegurar_path()` es idempotente: llamarlo dos veces no duplica la entrada.

⚠️ El orden importa. `proyecto_final/app.py` existe (es un shim de
   compatibilidad), así que si su carpeta entrase ANTES que la nuestra en el
   sys.path, `import app` traería ese módulo en vez de nuestro paquete.
   Por eso lo añadimos al FINAL (append), nunca al principio.
"""
from __future__ import annotations

import sys
from pathlib import Path

# proyecto_llmops/app/_proyecto_final.py → curso_ejemplos/proyecto_final/
_RUTA_PF = Path(__file__).resolve().parent.parent.parent / "proyecto_final"


def _asegurar_path() -> None:
    """Añade proyecto_final/ al sys.path si no está. Al final, nunca al principio."""
    ruta = str(_RUTA_PF)
    if ruta not in sys.path:
        sys.path.append(ruta)


_asegurar_path()

# Estos imports solo funcionan tras _asegurar_path(). Van aquí, juntos y a la
# vista, para que el resto del proyecto haga `from app._proyecto_final import X`.
import audit          # noqa: E402  el molde HallazgoCalidad y el log de auditoría
import graph_builder  # noqa: E402  el ensamblado del agente ReAct
import rag as rag_pf  # noqa: E402  el RAG del prototipo (trocear, contexto…)

__all__ = ["audit", "graph_builder", "rag_pf", "_RUTA_PF"]
