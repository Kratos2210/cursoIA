"""
frontend.py · La página de chat, leída UNA vez al importar
==========================================================
FINALIDAD:
  Cargar el HTML+CSS+JS de `app/static/chat.html` en una constante que la ruta
  `GET /` sirva tal cual. Es un módulo fino a propósito: el frontend es un archivo
  estático, no lógica de servidor.

⭐ Leerlo UNA vez, al importar, y no en cada request: el archivo no cambia
   mientras el proceso vive. El `--reload` de uvicorn re-importa este módulo al
   detectar el cambio, así que en desarrollo tampoco molesta.

⭐ Una constante y no FileResponse/StaticFiles: así `PAGINA_CHAT` es un string
   importable SIN levantar la app — un test puede afirmar que contiene lo que debe
   (el fetch a /chat, los botones de voto) sin un TestClient.
"""
from __future__ import annotations

from pathlib import Path

_RUTA_PAGINA = Path(__file__).parent / "static" / "chat.html"

PAGINA_CHAT: str = _RUTA_PAGINA.read_text(encoding="utf-8")
