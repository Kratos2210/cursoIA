#!/usr/bin/env python3
"""Genera el audio pregenerado del "modo escucha" con TTS neural (edge-tts).

Para cada MÓDULO del curso (los que renderizan /concepto/[slug]; los `extras`
del manifest NO llevan botón de escuchar) arma un texto de narración a partir
de:

    - `title`  y `goals` del manifest (`content/modules.manifest.json`)
    - el bloque <Recap>…</Recap> del MDX (`content/modules/<slug>.mdx`),
      quitando el <Arch> interno (rutas de archivo, no se narran) y limpiando
      símbolos/emojis para que la voz respire.

y produce `public/audio/<slug>.mp3` con la voz neural es-PE-CamilaNeural.

En la web, ListenButton.tsx reproduce ese mp3 y sólo si falla (404 porque no
se generó) cae al SpeechSynthesis del navegador.

Uso (dependencia única, sin instalar nada global):

    uv run --with edge-tts python web/scripts/generar-audio.py            # incremental
    uv run --with edge-tts python web/scripts/generar-audio.py --force    # regenera todo
    uv run --with edge-tts python web/scripts/generar-audio.py --solo 27-fundamentos-del-llm
    uv run --with edge-tts python web/scripts/generar-audio.py --voice es-MX-DaliaNeural

edge-tts necesita red (endpoint de Microsoft). Si está bloqueada, cada archivo
falla con un mensaje claro y el script sigue con los demás; no aborta.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

# --- Rutas (relativas a web/, este script vive en web/scripts/) -------------
WEB_DIR = Path(__file__).resolve().parent.parent
MANIFEST = WEB_DIR / "content" / "modules.manifest.json"
MODULES_DIR = WEB_DIR / "content" / "modules"
AUDIO_DIR = WEB_DIR / "public" / "audio"

DEFAULT_VOICE = "es-PE-CamilaNeural"
DEFAULT_RATE = "-5%"

# --- Limpieza del texto para narración --------------------------------------

# Símbolos que se traducen a palabras/pausas legibles en voz alta.
SYMBOL_MAP = {
    "→": " a ",
    "⊃": " contiene ",
    "×": " por ",
    "·": ", ",
    "—": ", ",
    "–": ", ",
    "&": " y ",
}

# Bloque de rangos Unicode de emojis/pictogramas a eliminar por completo.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # símbolos y pictogramas, emoticonos, etc.
    "\U00002600-\U000027BF"  # misceláneos y dingbats (⭐ ✔ ⛔ ↺ ✅ …)
    "\U00002190-\U000021FF"  # flechas (excepto → que ya se mapea antes)
    "\U00002B00-\U00002BFF"  # flechas/estrellas extra (◆ ◈ etc. viven aquí y en 25A0)
    "\U000025A0-\U000025FF"  # formas geométricas (◆ ◈ ◇ …)
    "\U0001F000-\U0001F0FF"
    "\U0000FE00-\U0000FE0F"  # selectores de variación
    "\U00002B50"
    "\U0000200D"             # zero-width joiner
    "]+",
    flags=re.UNICODE,
)


def limpiar(texto: str) -> str:
    """Deja el texto listo para leer en voz alta.

    Convierte markdown/MDX y símbolos en palabras naturales; quita emojis,
    backticks y énfasis; colapsa espacios.
    """
    t = texto

    # Etiquetas MDX/HTML residuales (p. ej. si quedara algo tras quitar <Arch>).
    t = re.sub(r"<[^>]+>", " ", t)

    # Links markdown [texto](url) -> texto
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)

    # Traducción de símbolos a palabras/pausas (→ antes que el barrido de flechas).
    for sym, rep in SYMBOL_MAP.items():
        t = t.replace(sym, rep)

    # Emojis y pictogramas fuera.
    t = _EMOJI_RE.sub(" ", t)

    # Énfasis markdown: **negrita**, *cursiva*, ~~tachado~~ -> texto plano.
    t = t.replace("**", "").replace("~~", "").replace("*", "").replace("~", "")

    # Backticks: `código` -> código (y quita paréntesis vacíos de funciones).
    t = t.replace("`", "")
    t = re.sub(r"\(\s*\)", "", t)  # crear_llm() -> crear_llm

    # Identificadores con guión bajo: crear_llm -> crear llm
    t = t.replace("_", " ")

    # Barras y símbolos sueltos que estorban a la voz.
    t = t.replace("/", " o ").replace("\\", " ")
    t = t.replace("|", " ").replace("=", " ").replace("+", " más ")
    t = t.replace("@", "")

    # Comillas tipográficas y rectas -> nada (la voz no las necesita).
    t = re.sub(r'["“”«»]', "", t)

    # Normaliza puntuación: espacios antes de signos, comas/puntos repetidos.
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"(,\s*){2,}", ", ", t)
    t = re.sub(r"\.{2,}", ".", t)
    t = re.sub(r",\s*\.", ".", t)

    # Colapsa espacios y líneas.
    t = re.sub(r"\s+", " ", t).strip()
    # Limpia una posible coma/punto inicial tras el barrido de símbolos.
    t = re.sub(r"^[\s,;:.]+", "", t)
    return t


def extraer_recap(mdx: str) -> str:
    """Devuelve el contenido narrable del <Recap>, ya sin <Arch> ni etiquetas."""
    m = re.search(r"<Recap[^>]*>(.*?)</Recap>", mdx, re.S)
    if not m:
        return ""
    cuerpo = m.group(1)
    # El <Arch> lleva rutas de archivo: fuera antes de cualquier otra cosa.
    cuerpo = re.sub(r"<Arch>.*?</Arch>", " ", cuerpo, flags=re.S)
    return limpiar(cuerpo)


def texto_narracion(modulo: dict, mdx: str) -> str:
    """Arma la narración final: título + objetivos (si hay) + recap."""
    # `.rstrip` de puntuación evita el ".." cuando el campo ya venía con punto.
    title = limpiar(modulo.get("title", "")).rstrip(".,;: ")
    recap = extraer_recap(mdx)

    partes = [f"{title}."]

    goals = modulo.get("goals")
    if goals:
        # Quita el emoji/prefijo inicial ("🎯 Al terminar sabrás: …").
        objetivos = limpiar(goals)
        objetivos = re.sub(r"^[^A-Za-zÁÉÍÓÚÜáéíóúüñÑ]*", "", objetivos).strip()
        objetivos = objetivos.rstrip(".,;: ")
        if objetivos:
            partes.append(f"{objetivos}.")

    if recap:
        partes.append(f"En una frase: {recap}")

    texto = " ".join(partes)
    # Asegura que termina con punto para que la voz cierre la entonación.
    if texto and texto[-1] not in ".!?":
        texto += "."
    return texto


# --- Generación con edge-tts ------------------------------------------------


async def sintetizar(texto: str, destino: Path, voice: str, rate: str) -> None:
    import edge_tts  # import diferido: sólo se necesita al generar de verdad

    communicate = edge_tts.Communicate(texto, voice, rate=rate)
    await communicate.save(str(destino))


def necesita_regenerar(mp3: Path, mdx: Path, force: bool) -> bool:
    if force or not mp3.exists():
        return True
    # Incremental: regenera si el MDX es más nuevo que el mp3.
    return mdx.stat().st_mtime > mp3.stat().st_mtime


def humano(nbytes: int) -> str:
    kb = nbytes / 1024
    if kb < 1024:
        return f"{kb:6.1f} KB"
    return f"{kb / 1024:6.2f} MB"


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera los mp3 del modo escucha con edge-tts.")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"Voz de edge-tts (def. {DEFAULT_VOICE}).")
    parser.add_argument("--solo", metavar="SLUG", help="Genera sólo ese slug.")
    parser.add_argument("--force", action="store_true", help="Regenera todo, ignorando fechas.")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    modulos = manifest.get("modules", [])
    if args.solo:
        modulos = [m for m in modulos if m["slug"] == args.solo]
        if not modulos:
            print(f"❌ No hay ningún módulo con slug '{args.solo}'.", file=sys.stderr)
            return 1

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    filas: list[tuple[str, int, str]] = []
    total_bytes = 0

    for modulo in modulos:
        slug = modulo["slug"]
        mdx_path = MODULES_DIR / f"{slug}.mdx"
        mp3_path = AUDIO_DIR / f"{slug}.mp3"

        if not mdx_path.exists():
            print(f"⚠️  {slug}: no existe {mdx_path.name}, se omite.")
            filas.append((slug, 0, "error"))
            continue

        if not necesita_regenerar(mp3_path, mdx_path, args.force):
            filas.append((slug, mp3_path.stat().st_size, "saltado"))
            total_bytes += mp3_path.stat().st_size
            continue

        texto = texto_narracion(modulo, mdx_path.read_text(encoding="utf-8"))
        try:
            asyncio.run(sintetizar(texto, mp3_path, args.voice, DEFAULT_RATE))
            size = mp3_path.stat().st_size
            if size == 0:
                raise RuntimeError("edge-tts devolvió un archivo vacío (¿sin red?)")
            filas.append((slug, size, "generado"))
            total_bytes += size
            print(f"✔ {slug}  ({humano(size)})")
        except Exception as exc:  # noqa: BLE001 — queremos seguir con los demás
            # Típicamente: red bloqueada hacia el endpoint de Microsoft.
            if mp3_path.exists() and mp3_path.stat().st_size == 0:
                mp3_path.unlink()  # no dejar mp3 vacío que rompa la web
            print(f"❌ {slug}: {type(exc).__name__}: {exc}", file=sys.stderr)
            filas.append((slug, 0, "error"))

    # --- Tabla resumen ------------------------------------------------------
    print()
    print(f"{'slug':<34} {'tamaño':>10}  estado")
    print("-" * 60)
    for slug, size, estado in filas:
        tam = humano(size) if size else "       — "
        print(f"{slug:<34} {tam:>10}  {estado}")
    print("-" * 60)
    generados = sum(1 for _, _, e in filas if e == "generado")
    errores = sum(1 for _, _, e in filas if e == "error")
    print(f"Total: {total_bytes / (1024 * 1024):.2f} MB en {AUDIO_DIR}")
    print(f"Generados: {generados} · Saltados: {sum(1 for _, _, e in filas if e == 'saltado')} · Errores: {errores}")

    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
