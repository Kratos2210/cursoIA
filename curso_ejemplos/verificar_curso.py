"""
verificar_curso.py · Guardián de la coherencia del material del curso
=====================================================================
FINALIDAD:
  El material del curso vive en tres archivos que deben contarse la MISMA
  historia: `curso-langchain.html` (la web), `README.md` (la guía) y `util.py`
  (el código). Es facilísimo cambiar un modelo en el código y olvidar la web,
  o mover una sección del HTML y dejar un enlace de menú apuntando al vacío.
  Este script hace, de una pasada y sin red ni llaves, cuatro comprobaciones:

    (a) ANCLAS: cada enlace interno `href="#X"` del HTML tiene su `id="X"`.
    (b) DOCTYPE: el HTML NO trae `DOCTYPE` (lo inyecta la herramienta que publica;
        si el archivo ya lo trae, la página sale con doble carcasa y se rompe).
    (c) MODELOS: los 7 modelos por defecto de la tabla del cheat sheet coinciden,
        proveedor a proveedor, con `util.MODELOS_POR_DEFECTO` (la fuente de verdad).
    (d) TABLAS: la tabla de módulos del mapa (HTML) y la tabla §5 del README
        listan las mismas filas (se espejan).

  Imprime un informe legible y termina con código de salida 0 si todo cuadra o 1
  si algo falla, para poder colgarlo de la CI (`uv run python verificar_curso.py`).

POR QUÉ ASÍ (decisiones de diseño):
  - Usamos `html.parser` de la biblioteca ESTÁNDAR y no BeautifulSoup: el curso no
    añade dependencias por comodidad (la stdlib basta para leer atributos y tablas).
  - Cada chequeo es una función PURA que recibe texto y devuelve un ResultadoChequeo.
    Así se testean con fixtures pequeñas inline, sin tocar los archivos reales ni
    capturar stdout. La capa que lee ficheros e imprime/sale vive aparte, en main().
  - El material (HTML/README/util) es de SOLO LECTURA: si aquí salta un fallo, se
    corrige el material a conciencia; el verificador no se "afloja" para callarlo.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

import util  # la fuente de verdad de los modelos por defecto

# Rutas por defecto: relativas a ESTE archivo, no al directorio actual, para que
# el script funcione desde cualquier CWD (terminal, CI, editor…).
CARPETA = Path(__file__).resolve().parent
HTML_POR_DEFECTO = CARPETA / "curso-langchain.html"
README_POR_DEFECTO = CARPETA / "README.md"


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
# Parser HTML base: recolecta los `id` y los `href="#…"` en UNA pasada
# ------------------------------------------------------------------
class _RecolectorAnclas(HTMLParser):
    """Recorre el HTML y anota todos los `id` (destinos) y los `href="#…"` (orígenes).

    Por qué un parser y no una regex suelta: el HTML del curso lleva ejemplos de
    código embebidos donde aparecen textos como `id=...`; el parser solo mira
    atributos de etiquetas reales, así que no se confunde.
    """

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.enlaces_internos: list[str] = []  # los X de cada href="#X" (con orden)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for nombre, valor in attrs:
            if valor is None:
                continue
            if nombre == "id":
                self.ids.add(valor)
            elif nombre == "href" and valor.startswith("#") and len(valor) > 1:
                # len > 1 descarta el href="#" pelado (no apunta a ninguna sección).
                self.enlaces_internos.append(valor[1:])


def verificar_anclas(html: str) -> ResultadoChequeo:
    """(a) Todo `href="#X"` debe tener en el documento un elemento con `id="X"`."""
    parser = _RecolectorAnclas()
    parser.feed(html)
    # Comparamos contra el conjunto de ids; reportamos cada enlace roto una vez.
    rotos = sorted({x for x in parser.enlaces_internos if x not in parser.ids})
    if rotos:
        detalles = [f'href="#{x}" no tiene un elemento con id="{x}".' for x in rotos]
        return ResultadoChequeo("Anclas internas", False, detalles)
    total = len(set(parser.enlaces_internos))
    return ResultadoChequeo(
        "Anclas internas", True, [f"{total} enlaces internos, todos con destino."]
    )


def verificar_sin_doctype(html: str) -> ResultadoChequeo:
    """(b) El HTML no debe contener `DOCTYPE` en ninguna capitalización."""
    # Insensible a mayúsculas porque cualquier variante (<!DOCTYPE>, <!doctype>)
    # rompe igual la publicación.
    if "doctype" in html.lower():
        return ResultadoChequeo(
            "Sin DOCTYPE",
            False,
            ["el HTML contiene 'DOCTYPE'; la carcasa la inyecta la herramienta de "
             "publicación, así que el archivo NO debe traerlo."],
        )
    return ResultadoChequeo("Sin DOCTYPE", True, ["el HTML no contiene DOCTYPE."])


# ------------------------------------------------------------------
# Helpers de extracción de tablas (compartidos por los chequeos c y d)
# ------------------------------------------------------------------
def _texto_plano(fragmento_html: str) -> str:
    """Quita etiquetas de un fragmento HTML y colapsa espacios.

    Convierte `<a ...>04</a>` y `<code>x</code>` en su texto interior, que es lo
    que queremos comparar (no la maqueta).
    """
    sin_tags = re.sub(r"<[^>]+>", "", fragmento_html)
    return re.sub(r"\s+", " ", sin_tags).strip()


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


def _seccion_html(html: str, id_seccion: str) -> str:
    """Devuelve el HTML desde `id="<id_seccion>"` hasta el próximo `<section` (o el final).

    Nos permite acotar la búsqueda de una tabla a su sección (#cheat, #mapa…).
    """
    inicio = html.find(f'id="{id_seccion}"')
    if inicio == -1:
        return ""
    resto = html[inicio:]
    siguiente = resto.find("<section", 1)  # el 1 salta la sección actual
    return resto if siguiente == -1 else resto[:siguiente]


def _filas_tabla_html(seccion_html: str, texto_en_thead: str) -> list[list[str]]:
    """Extrae las filas (lista de celdas de texto) de la tabla cuyo <thead> contiene
    `texto_en_thead`. Devuelve [] si no encuentra esa tabla."""
    for tabla in re.findall(r"<table>(.*?)</table>", seccion_html, re.S):
        thead = re.search(r"<thead>(.*?)</thead>", tabla, re.S)
        if not thead or texto_en_thead not in thead.group(1):
            continue
        cuerpo = re.search(r"<tbody>(.*?)</tbody>", tabla, re.S)
        if not cuerpo:
            return []
        filas = []
        for fila in re.findall(r"<tr>(.*?)</tr>", cuerpo.group(1), re.S):
            celdas = [_texto_plano(td) for td in re.findall(r"<td>(.*?)</td>", fila, re.S)]
            if celdas:
                filas.append(celdas)
        return filas
    return []


def verificar_modelos(html: str, modelos: dict[str, str]) -> ResultadoChequeo:
    """(c) La tabla `proveedor → modelo` del cheat sheet coincide con MODELOS_POR_DEFECTO."""
    seccion = _seccion_html(html, "cheat")
    # La tabla de defaults es la que en su encabezado dice "Modelo por defecto".
    filas = _filas_tabla_html(seccion, "Modelo por defecto")
    if not filas:
        return ResultadoChequeo(
            "Modelos por defecto", False,
            ["no se encontró la tabla de modelos por defecto en la sección #cheat."],
        )
    # Cada fila: <code>proveedor</code> | <code>modelo</code> | <code>LLAVE</code>.
    en_html = {fila[0].strip(): fila[1].strip() for fila in filas if len(fila) >= 2}

    detalles: list[str] = []
    for proveedor, modelo in sorted(modelos.items()):
        if proveedor not in en_html:
            detalles.append(f"'{proveedor}': está en util.MODELOS_POR_DEFECTO pero no en el HTML.")
        elif en_html[proveedor] != modelo:
            detalles.append(
                f"'{proveedor}': HTML dice '{en_html[proveedor]}' pero util dice '{modelo}'."
            )
    for proveedor in sorted(en_html):
        if proveedor not in modelos:
            detalles.append(f"'{proveedor}': está en el HTML pero no en util.MODELOS_POR_DEFECTO.")

    if detalles:
        return ResultadoChequeo("Modelos por defecto", False, detalles)
    return ResultadoChequeo(
        "Modelos por defecto", True,
        [f"cheat sheet == util.MODELOS_POR_DEFECTO ({len(modelos)} proveedores)."],
    )


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


# Columnas de la tabla de módulos: Concepto | Ejemplo | Ejercicio | Test.
# Comparamos Concepto+Ejemplo+Test (índices 0,1,3) y EXCLUIMOS Ejercicio (índice 2):
# esa columna enlaza a destinos distintos por diseño (anclas del HTML vs archivos del
# README) e incluso con etiquetas distintas, así que compararla daría falsos positivos.
_COLUMNAS_ESPEJO = (0, 1, 3)


def _clave_fila(celdas: list[str]) -> tuple[str, ...]:
    """La huella normalizada de una fila usando solo las columnas que deben espejarse."""
    return tuple(_normalizar_celda(celdas[i]) for i in _COLUMNAS_ESPEJO if i < len(celdas))


def verificar_tablas_modulos(html: str, readme_md: str) -> ResultadoChequeo:
    """(d) La tabla de módulos de #mapa y la §5 del README listan las mismas filas."""
    filas_html = _filas_tabla_html(_seccion_html(html, "mapa"), "Concepto")
    filas_md = _filas_tabla_markdown(readme_md, "## 5)")
    if not filas_html or not filas_md:
        return ResultadoChequeo(
            "Tabla de módulos", False,
            ["no se pudo extraer alguna de las dos tablas de módulos (HTML #mapa o §5 del README)."],
        )

    claves_html = {_clave_fila(f) for f in filas_html}
    claves_md = {_clave_fila(f) for f in filas_md}

    detalles: list[str] = []
    for clave in sorted(claves_html - claves_md):
        detalles.append(f"fila en el HTML #mapa pero NO en la §5 del README: {clave}")
    for clave in sorted(claves_md - claves_html):
        detalles.append(f"fila en la §5 del README pero NO en el HTML #mapa: {clave}")

    if detalles:
        return ResultadoChequeo("Tabla de módulos", False, detalles)
    return ResultadoChequeo(
        "Tabla de módulos", True,
        [f"#mapa == §5 del README ({len(claves_html)} filas, columnas Concepto/Ejemplo/Test)."],
    )


# ------------------------------------------------------------------
# Orquestación: leer los archivos reales, correr todo, informar y salir
# ------------------------------------------------------------------
def ejecutar_chequeos(html: str, readme_md: str) -> list[ResultadoChequeo]:
    """Corre los cuatro chequeos sobre los textos dados y devuelve sus resultados."""
    return [
        verificar_anclas(html),
        verificar_sin_doctype(html),
        verificar_modelos(html, util.MODELOS_POR_DEFECTO),
        verificar_tablas_modulos(html, readme_md),
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


def main(ruta_html: Path = HTML_POR_DEFECTO, ruta_readme: Path = README_POR_DEFECTO) -> int:
    """Punto de entrada CLI: devuelve 0 si todo pasa, 1 si algo falla."""
    for ruta in (ruta_html, ruta_readme):
        if not ruta.exists():
            print(f"[FALLO] No existe el archivo requerido: {ruta}")
            return 1

    html = ruta_html.read_text(encoding="utf-8")
    readme_md = ruta_readme.read_text(encoding="utf-8")

    resultados = ejecutar_chequeos(html, readme_md)
    print(formatear_informe(resultados))
    # Exit code apto para CI: 1 si al menos un chequeo falla.
    return 0 if all(r.ok for r in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
