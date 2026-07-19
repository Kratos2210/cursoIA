"""
verificar_curso.py · Guardián de la coherencia del material del curso
=====================================================================
FINALIDAD:
  El material del curso vive en tres lugares que deben contarse la MISMA
  historia: la web Next.js (`web/content`: manifest + MDX — la fuente de verdad
  del alumno), `README.md` (la guía del repo) y `util.py` (el código). Es
  facilísimo cambiar un modelo en el código y olvidar el cheat sheet, o mover
  un módulo y dejar un enlace apuntando al vacío. Este script hace, de una
  pasada y sin red, llaves ni build de node, siete comprobaciones:

    (a) MODELOS: la tabla del cheat sheet de la web (`extras/cheat-sheet.mdx`)
        coincide, proveedor a proveedor, con `util.MODELOS_POR_DEFECTO`.
    (b) TABLAS: la tabla de módulos del mapa de la web (`extras/mapa.mdx`) y la
        tabla §5 del README listan las mismas filas (se espejan).
    (c) MANIFEST: total == módulos + extras; `order` == posición en el array
        (la navegación sale del ORDEN del array); slug ↔ archivo .mdx 1:1.
    (d) PYFILES: cada `pyFile` del manifest existe en `curso_ejemplos/`.
    (e) ENLACES WEB: todo `](/concepto/X)` y `](/recurso/X)` de los MDX apunta
        a un slug que existe en el manifest.
    (f) NIVELES: el `<Recap level={N}>` de cada módulo == su `level` del
        manifest, y el PRIMER módulo de cada ruta abre con `<LevelBanner>` del
        nivel correcto (todo banner debe llevar el nivel de SU ruta).
    (g) MDX: cada módulo conserva la pauta pedagógica (Quiz, Checkpoint, Recap,
        práctica) y ningún `<` va pegado a un dígito fuera de código (MDX lo
        lee como JSX y el build revienta).

  Imprime un informe legible y termina con código de salida 0 si todo cuadra o 1
  si algo falla, para poder colgarlo de la CI (`uv run python verificar_curso.py`).

POR QUÉ ASÍ (decisiones de diseño):
  - Biblioteca ESTÁNDAR solamente (`re`, `json`, `pathlib`): el curso no añade
    dependencias por comodidad; para tablas markdown y JSX simple, regex basta.
  - Cada chequeo es una función PURA que recibe texto/datos y devuelve un
    ResultadoChequeo. Así se testean con fixtures pequeñas inline, sin tocar los
    archivos reales ni capturar stdout. La capa que lee ficheros e imprime/sale
    vive aparte, en main().
  - El material (web/README/util) es de SOLO LECTURA: si aquí salta un fallo, se
    corrige el material a conciencia; el verificador no se "afloja" para callarlo.

NOTA HISTÓRICA: hasta 2026-07-19 este script también validaba el HTML monolítico
`curso-langchain.html` (anclas, doctype, sus tablas). Ese archivo se retiró: la
web Next.js es la única fuente de verdad, y sus espejos se verifican aquí.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import util  # la fuente de verdad de los modelos por defecto

# Rutas por defecto: relativas a ESTE archivo, no al directorio actual, para que
# el script funcione desde cualquier CWD (terminal, CI, editor…).
CARPETA = Path(__file__).resolve().parent
README_POR_DEFECTO = CARPETA / "README.md"
WEB_POR_DEFECTO = CARPETA.parent / "web" / "content"


@dataclass
class ResultadoChequeo:
    """El veredicto de un chequeo: su nombre, si pasó y, si no, por qué.

    Invariante: si hay `detalles`, entonces `ok` es False. Separar el dato del
    print permite testear la lógica sin leer la salida por pantalla.
    """
    nombre: str
    ok: bool
    detalles: list[str] = field(default_factory=list)


# ------------------------------------------------------------------
# Helpers de extracción de tablas markdown (chequeos a y b)
# ------------------------------------------------------------------
def _normalizar_celda(texto: str) -> str:
    """Normaliza el texto de una celda para comparar HTML contra Markdown.

    Ambos formatos decoran igual el contenido pero con sintaxis distinta. Para
    compararlos sin falsos positivos:
      - los enlaces Markdown `[texto](url)` se reducen a `texto`;
      - se quitan los adornos de énfasis: comillas invertidas, `*`, `_` y los
        paréntesis que envuelven notas (p. ej. Markdown escribe `*(nota)*` donde
        el HTML pone `<em>nota</em>`);
      - se colapsan espacios.
    """
    texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)  # [texto](url) -> texto
    texto = re.sub(r"[`*_()]", "", texto)                    # adornos de énfasis
    return re.sub(r"\s+", " ", texto).strip()


def _filas_tabla_markdown(readme_md: str, titulo_seccion: str) -> list[list[str]]:
    """Extrae las filas de DATOS de la primera tabla Markdown tras el encabezado dado.

    En Markdown la tabla es: fila de cabecera, línea separadora `|---|` y luego el
    cuerpo. Solo queremos las filas de datos, así que empezamos a recolectar DESPUÉS
    de ver la línea separadora; así la cabecera queda excluida, igual que el `<thead>`
    queda fuera cuando extraemos la tabla del HTML (si no, la cabecera se compararía
    contra nada y daría un falso positivo).
    """
    inicio = readme_md.find(titulo_seccion)
    if inicio == -1:
        return []
    filas: list[list[str]] = []
    tras_separador = False
    for linea in readme_md[inicio:].splitlines():
        recorte = linea.strip()
        if not recorte.startswith("|"):
            # La tabla termina en la primera línea que ya no es una fila.
            if filas:
                break
            continue
        if set(recorte) <= set("|-: "):  # la línea separadora |---|---|
            tras_separador = True
            continue
        if not tras_separador:
            continue  # es la fila de cabecera; la ignoramos
        celdas = [c.strip() for c in recorte.strip("|").split("|")]
        filas.append(celdas)
    return filas


def verificar_modelos(cheat_md: str, modelos: dict[str, str]) -> ResultadoChequeo:
    """(a) La tabla `proveedor → modelo` del cheat sheet de la web == MODELOS_POR_DEFECTO."""
    # La tabla de defaults es la que en su cabecera dice "Modelo por defecto".
    filas = _filas_tabla_markdown(cheat_md, "Modelo por defecto")
    if not filas:
        return ResultadoChequeo(
            "Modelos por defecto", False,
            ["no se encontró la tabla de modelos por defecto en el cheat sheet de la web."],
        )
    # Cada fila: `proveedor` | `modelo` | `LLAVE`; _normalizar_celda quita los backticks.
    en_web = {
        _normalizar_celda(fila[0]): _normalizar_celda(fila[1])
        for fila in filas if len(fila) >= 2
    }

    detalles: list[str] = []
    for proveedor, modelo in sorted(modelos.items()):
        if proveedor not in en_web:
            detalles.append(f"'{proveedor}': está en util.MODELOS_POR_DEFECTO pero no en el cheat sheet.")
        elif en_web[proveedor] != modelo:
            detalles.append(
                f"'{proveedor}': el cheat sheet dice '{en_web[proveedor]}' pero util dice '{modelo}'."
            )
    for proveedor in sorted(en_web):
        if proveedor not in modelos:
            detalles.append(f"'{proveedor}': está en el cheat sheet pero no en util.MODELOS_POR_DEFECTO.")

    if detalles:
        return ResultadoChequeo("Modelos por defecto", False, detalles)
    return ResultadoChequeo(
        "Modelos por defecto", True,
        [f"cheat sheet == util.MODELOS_POR_DEFECTO ({len(modelos)} proveedores)."],
    )


# Columnas de la tabla de módulos: Concepto | Ejemplo | Ejercicio | Test.
# Comparamos Concepto+Ejemplo+Test (índices 0,1,3) y EXCLUIMOS Ejercicio (índice 2):
# esa columna enlaza a destinos distintos por diseño (rutas de la web vs archivos del
# README) e incluso con etiquetas distintas, así que compararla daría falsos positivos.
_COLUMNAS_ESPEJO = (0, 1, 3)


def _clave_fila(celdas: list[str]) -> tuple[str, ...]:
    """La huella normalizada de una fila usando solo las columnas que deben espejarse."""
    return tuple(_normalizar_celda(celdas[i]) for i in _COLUMNAS_ESPEJO if i < len(celdas))


def verificar_tablas_modulos(mapa_md: str, readme_md: str) -> ResultadoChequeo:
    """(b) La tabla del mapa de la web y la §5 del README listan las mismas filas."""
    filas_web = _filas_tabla_markdown(mapa_md, "| Concepto |")
    filas_md = _filas_tabla_markdown(readme_md, "## 5)")
    if not filas_web or not filas_md:
        return ResultadoChequeo(
            "Tabla de módulos", False,
            ["no se pudo extraer alguna de las dos tablas de módulos (mapa de la web o §5 del README)."],
        )

    claves_web = {_clave_fila(f) for f in filas_web}
    claves_md = {_clave_fila(f) for f in filas_md}

    detalles: list[str] = []
    for clave in sorted(claves_web - claves_md):
        detalles.append(f"fila en el mapa de la web pero NO en la §5 del README: {clave}")
    for clave in sorted(claves_md - claves_web):
        detalles.append(f"fila en la §5 del README pero NO en el mapa de la web: {clave}")

    if detalles:
        return ResultadoChequeo("Tabla de módulos", False, detalles)
    return ResultadoChequeo(
        "Tabla de módulos", True,
        [f"mapa de la web == §5 del README ({len(claves_web)} filas, columnas Concepto/Ejemplo/Test)."],
    )


# ------------------------------------------------------------------
# Chequeos de la WEB (web/content): manifest, pyFiles, enlaces, niveles, MDX
# ------------------------------------------------------------------
def verificar_manifest(manifest: dict, slugs_modulos_disco: set[str],
                       slugs_extras_disco: set[str]) -> ResultadoChequeo:
    """(e) El manifest se cuenta a sí mismo la verdad y espeja el disco 1:1.

    La navegación (prev/next y el roadmap) sale del ORDEN del array `modules`,
    y `order` debe acompañarlo: si divergen, el sitio muestra un orden y el
    campo cuenta otro.
    """
    modulos = manifest.get("modules", [])
    extras = manifest.get("extras", [])
    detalles: list[str] = []

    total = manifest.get("total")
    if total != len(modulos) + len(extras):
        detalles.append(
            f"total dice {total} pero hay {len(modulos)} módulos + {len(extras)} extras."
        )
    for indice, modulo in enumerate(modulos):
        if modulo.get("order") != indice:
            detalles.append(
                f"'{modulo.get('slug')}': order={modulo.get('order')} pero ocupa la posición {indice}."
            )

    slugs_manifest = {m["slug"] for m in modulos}
    slugs_extras = {e["slug"] for e in extras}
    for slug in sorted(slugs_manifest - slugs_modulos_disco):
        detalles.append(f"módulo '{slug}' está en el manifest pero no tiene .mdx en disco.")
    for slug in sorted(slugs_modulos_disco - slugs_manifest):
        detalles.append(f"archivo '{slug}.mdx' (módulo) no aparece en el manifest.")
    for slug in sorted(slugs_extras - slugs_extras_disco):
        detalles.append(f"extra '{slug}' está en el manifest pero no tiene .mdx en disco.")
    for slug in sorted(slugs_extras_disco - slugs_extras):
        detalles.append(f"archivo '{slug}.mdx' (extra) no aparece en el manifest.")

    if detalles:
        return ResultadoChequeo("Manifest de la web", False, detalles)
    return ResultadoChequeo(
        "Manifest de la web", True,
        [f"{len(modulos)} módulos + {len(extras)} extras, order == posición, disco 1:1."],
    )


def verificar_pyfiles(manifest: dict, existe: Callable[[str], bool]) -> ResultadoChequeo:
    """(f) Cada `pyFile` que el manifest promete debe existir en curso_ejemplos/."""
    rotos = [
        f"'{m['slug']}': pyFile '{m['pyFile']}' no existe."
        for m in manifest.get("modules", [])
        if m.get("pyFile") and not existe(m["pyFile"])
    ]
    if rotos:
        return ResultadoChequeo("pyFiles del manifest", False, rotos)
    total = sum(1 for m in manifest.get("modules", []) if m.get("pyFile"))
    return ResultadoChequeo(
        "pyFiles del manifest", True, [f"{total} pyFiles referenciados, todos existen."]
    )


# `](/concepto/x#seccion)` → captura "concepto"/"recurso" y el slug sin fragmento.
_RE_ENLACE_WEB = re.compile(r"\]\(/(concepto|recurso)/([^)#\s]+)")


def verificar_enlaces_web(mdx_por_nombre: dict[str, str], slugs_conceptos: set[str],
                          slugs_recursos: set[str]) -> ResultadoChequeo:
    """(g) Todo enlace interno de los MDX apunta a un slug que existe en el manifest."""
    destinos = {"concepto": slugs_conceptos, "recurso": slugs_recursos}
    rotos: list[str] = []
    total = 0
    for nombre, texto in sorted(mdx_por_nombre.items()):
        for tipo, slug in _RE_ENLACE_WEB.findall(texto):
            total += 1
            if slug not in destinos[tipo]:
                rotos.append(f"{nombre}: enlace a /{tipo}/{slug} sin destino en el manifest.")
    if rotos:
        return ResultadoChequeo("Enlaces internos de la web", False, rotos)
    return ResultadoChequeo(
        "Enlaces internos de la web", True, [f"{total} enlaces, todos con destino."]
    )


_RE_RECAP = re.compile(r"<Recap\s+level=\{(\d+)\}")
_RE_BANNER = re.compile(r"<LevelBanner\s+level=\{(\d+)\}")


def verificar_niveles(manifest: dict, mdx_por_slug: dict[str, str]) -> ResultadoChequeo:
    """(h) Recap y LevelBanner llevan el nivel de SU ruta según el manifest.

    Política del roadmap: el PRIMER módulo de cada ruta abre con LevelBanner, y
    cualquier banner (de apertura o interior) usa el color de la ruta en la que
    vive. Un banner con otro nivel pinta la ruta del color equivocado.
    """
    detalles: list[str] = []
    rutas_vistas: set[str] = set()
    for modulo in manifest.get("modules", []):
        slug, nivel = modulo["slug"], modulo["level"]
        texto = mdx_por_slug.get(slug, "")

        for encontrado in _RE_RECAP.findall(texto):
            if int(encontrado) != nivel:
                detalles.append(f"'{slug}': Recap level={{{encontrado}}} pero el manifest dice {nivel}.")
        for encontrado in _RE_BANNER.findall(texto):
            if int(encontrado) != nivel:
                detalles.append(f"'{slug}': LevelBanner level={{{encontrado}}} pero el manifest dice {nivel}.")

        # El primer módulo de cada ruta (en orden del array) DEBE abrirla con banner.
        ruta = modulo["levelName"]
        if ruta not in rutas_vistas:
            rutas_vistas.add(ruta)
            if not _RE_BANNER.search(texto):
                detalles.append(f"'{slug}' abre la ruta '{ruta}' pero no tiene LevelBanner.")

    if detalles:
        return ResultadoChequeo("Niveles (Recap y LevelBanner)", False, detalles)
    return ResultadoChequeo(
        "Niveles (Recap y LevelBanner)", True,
        [f"{len(rutas_vistas)} rutas abiertas con banner; todos los niveles == manifest."],
    )


# La pauta pedagógica mínima de un módulo (patrón, etiqueta para el informe).
_PAUTA_MDX = (
    ("<Quiz", "Quiz"),
    ("<Checkpoint", "Checkpoint"),
    ("<Recap", "Recap"),
    ('kind="practice"', "práctica"),
)


def _lineas_sin_codigo(mdx: str) -> list[tuple[int, str]]:
    """Las líneas de un MDX que NO son código (ni fence ``` ni `inline`).

    Devuelve pares (número de línea 1-based, texto sin los tramos `inline`),
    para poder reportar la línea exacta de un hallazgo.
    """
    lineas: list[tuple[int, str]] = []
    dentro_de_fence = False
    for numero, linea in enumerate(mdx.splitlines(), start=1):
        if linea.lstrip().startswith("```"):
            dentro_de_fence = not dentro_de_fence
            continue
        if dentro_de_fence:
            continue
        lineas.append((numero, re.sub(r"`[^`]*`", "", linea)))
    return lineas


def verificar_mdx(mdx_por_slug: dict[str, str]) -> ResultadoChequeo:
    """(i) Pauta pedagógica completa y ningún `<` pegado a dígito fuera de código."""
    detalles: list[str] = []
    for slug, texto in sorted(mdx_por_slug.items()):
        faltan = [etiqueta for patron, etiqueta in _PAUTA_MDX if patron not in texto]
        if faltan:
            detalles.append(f"'{slug}': falta {', '.join(faltan)}.")
        for numero, linea in _lineas_sin_codigo(texto):
            if re.search(r"<\d", linea):
                detalles.append(
                    f"'{slug}' línea {numero}: '<' pegado a un dígito fuera de código "
                    "(MDX lo lee como JSX y el build revienta; escápalo)."
                )
    if detalles:
        return ResultadoChequeo("MDX de los módulos", False, detalles)
    return ResultadoChequeo(
        "MDX de los módulos", True,
        [f"{len(mdx_por_slug)} módulos con la pauta completa y sin trampas '<dígito'."],
    )


def ejecutar_chequeos_web(manifest: dict, mdx_modulos: dict[str, str],
                          mdx_extras: dict[str, str],
                          existe_pyfile: Callable[[str], bool]) -> list[ResultadoChequeo]:
    """Corre los cinco chequeos de la web sobre datos ya cargados (puro, testeable)."""
    slugs_conceptos = {m["slug"] for m in manifest.get("modules", [])}
    slugs_recursos = {e["slug"] for e in manifest.get("extras", [])}
    return [
        verificar_manifest(manifest, set(mdx_modulos), set(mdx_extras)),
        verificar_pyfiles(manifest, existe_pyfile),
        verificar_enlaces_web({**mdx_modulos, **mdx_extras}, slugs_conceptos, slugs_recursos),
        verificar_niveles(manifest, mdx_modulos),
        verificar_mdx(mdx_modulos),
    ]


# ------------------------------------------------------------------
# Orquestación: leer los archivos reales, correr todo, informar y salir
# ------------------------------------------------------------------
def ejecutar_chequeos(cheat_md: str, mapa_md: str, readme_md: str) -> list[ResultadoChequeo]:
    """Corre los chequeos de espejos (modelos y tablas) sobre los textos dados."""
    return [
        verificar_modelos(cheat_md, util.MODELOS_POR_DEFECTO),
        verificar_tablas_modulos(mapa_md, readme_md),
    ]


def formatear_informe(resultados: list[ResultadoChequeo]) -> str:
    """Arma el informe legible por humanos a partir de los resultados."""
    lineas = ["Verificador del curso", "====================="]
    for r in resultados:
        etiqueta = "[OK]   " if r.ok else "[FALLO]"
        # En verde basta un resumen; en rojo listamos cada detalle indentado.
        if r.ok:
            resumen = r.detalles[0] if r.detalles else ""
            lineas.append(f"{etiqueta} {r.nombre}: {resumen}")
        else:
            lineas.append(f"{etiqueta} {r.nombre}:")
            for d in r.detalles:
                lineas.append(f"        - {d}")
    lineas.append("")
    if all(r.ok for r in resultados):
        lineas.append("Todo coherente. ✅")
    else:
        lineas.append("Se encontraron incoherencias. ❌")
    return "\n".join(lineas)


def _leer_mdx(carpeta: Path) -> dict[str, str]:
    """{slug: contenido} de todos los .mdx de una carpeta (slug = nombre sin extensión)."""
    return {ruta.stem: ruta.read_text(encoding="utf-8") for ruta in sorted(carpeta.glob("*.mdx"))}


def main(ruta_readme: Path = README_POR_DEFECTO, ruta_web: Path = WEB_POR_DEFECTO) -> int:
    """Punto de entrada CLI: devuelve 0 si todo pasa, 1 si algo falla."""
    ruta_cheat = ruta_web / "extras" / "cheat-sheet.mdx"
    ruta_mapa = ruta_web / "extras" / "mapa.mdx"
    for ruta in (ruta_readme, ruta_web / "modules.manifest.json", ruta_cheat, ruta_mapa):
        if not ruta.exists():
            print(f"[FALLO] No existe el archivo requerido: {ruta}")
            return 1

    readme_md = ruta_readme.read_text(encoding="utf-8")
    manifest = json.loads((ruta_web / "modules.manifest.json").read_text(encoding="utf-8"))
    mdx_modulos = _leer_mdx(ruta_web / "modules")
    mdx_extras = _leer_mdx(ruta_web / "extras")

    resultados = ejecutar_chequeos(
        mdx_extras.get("cheat-sheet", ""), mdx_extras.get("mapa", ""), readme_md
    ) + ejecutar_chequeos_web(
        manifest, mdx_modulos, mdx_extras,
        existe_pyfile=lambda relativa: (CARPETA / relativa).exists(),
    )
    print(formatear_informe(resultados))
    # Exit code apto para CI: 1 si al menos un chequeo falla.
    return 0 if all(r.ok for r in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
