"""
frontend.py · La página de chat, leída UNA vez al importar
==========================================================
FINALIDAD:
  Cargar el HTML+CSS+JS de `app/static/chat.html` en una constante que la ruta
  `GET /` sirva tal cual. Nada más. Es un módulo fino a propósito: el frontend
  es un archivo estático, no lógica de servidor.

⭐ POR QUÉ leerlo UNA vez, al importar, y no en cada request:
  El archivo no cambia mientras el proceso vive, así que releerlo del disco en
  cada `GET /` sería trabajo de E/S por nada. Se lee al importar y queda en
  memoria (`PAGINA_CHAT`). El precio —que editar el HTML no se refleje sin
  reiniciar— no existe en desarrollo: el `--reload` de uvicorn RE-IMPORTA este
  módulo al detectar el cambio, y la relectura vuelve a ocurrir.

⭐ POR QUÉ una constante y no `FileResponse`/`StaticFiles`:
  Así `PAGINA_CHAT` es un simple string importable SIN levantar la app: un test
  puede afirmar que contiene lo que debe (fetch("/chat"), los botones de voto…)
  sin un TestClient. La ruta `GET /` solo lo envuelve en un `HTMLResponse`.
"""
from __future__ import annotations

from pathlib import Path

# El HTML vive al lado, en static/. `__file__` ancla la ruta al módulo, así el
# import funciona sea cual sea el directorio de trabajo desde el que se arranque.
_RUTA_PAGINA = Path(__file__).parent / "static" / "chat.html"

# La página entera, en memoria. Se lee una sola vez, al importar este módulo.
PAGINA_CHAT: str = _RUTA_PAGINA.read_text(encoding="utf-8")
