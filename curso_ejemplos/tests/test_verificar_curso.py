"""
test_verificar_curso.py · Tests del guardián de coherencia del curso
=====================================================================
FINALIDAD:
  `verificar_curso.py` vigila que la web (HTML), la guía (README) y el código
  (util.py) se cuenten la MISMA historia. Aquí protegemos cada uno de sus cuatro
  chequeos con fixtures HTML/Markdown INLINE y mínimas: nunca tocamos el material
  real, así los tests son deterministas, offline y no se rompen cuando el curso
  crece. Cada chequeo se prueba en su caso sano (ok=True) y en su caso roto
  (ok=False, con un detalle que nombra la incoherencia).

  El último bloque, además, cierra el bug del extractor Markdown: la fila de
  CABECERA de la tabla NO debe contar como fila de datos (si contara, el mapa de
  módulos daría un falso positivo aunque HTML y README estén espejados).
"""
import pytest

import verificar_curso


# ------------------------------------------------------------------
# (a) verificar_anclas: cada href="#X" tiene su id="X"
# ------------------------------------------------------------------
@pytest.mark.offline
class TestVerificarAnclas:
    def test_todas_las_anclas_tienen_destino(self):
        """Si cada enlace interno apunta a un id existente, el chequeo pasa."""
        html = (
            '<a href="#intro">ir</a>'
            '<section id="intro"><h2>Intro</h2></section>'
        )
        assert verificar_curso.verificar_anclas(html).ok is True

    def test_ancla_sin_destino_falla_y_nombra_el_enlace(self):
        """Un href="#x" sin su id="x" rompe el chequeo y el detalle nombra #x."""
        html = '<a href="#x">roto</a><section id="intro">sin x</section>'
        resultado = verificar_curso.verificar_anclas(html)
        assert resultado.ok is False
        assert any("#x" in d for d in resultado.detalles)


# ------------------------------------------------------------------
# (b) verificar_sin_doctype: el HTML NO debe traer DOCTYPE
# ------------------------------------------------------------------
@pytest.mark.offline
class TestVerificarSinDoctype:
    def test_html_sin_doctype_pasa(self):
        """Un HTML limpio (sin DOCTYPE) es lo correcto: la carcasa la pone la herramienta."""
        html = "<section id='intro'>hola</section>"
        assert verificar_curso.verificar_sin_doctype(html).ok is True

    @pytest.mark.parametrize(
        "doctype",
        ["<!DOCTYPE html>", "<!doctype html>", "<!Doctype html>"],
    )
    def test_doctype_en_cualquier_capitalizacion_falla(self, doctype):
        """Cualquier variante de DOCTYPE rompe la publicación, así que debe fallar."""
        html = f"{doctype}\n<section id='intro'>hola</section>"
        assert verificar_curso.verificar_sin_doctype(html).ok is False


# ------------------------------------------------------------------
# (c) verificar_modelos: la tabla del cheat sheet == MODELOS_POR_DEFECTO
# ------------------------------------------------------------------
def _html_cheat(filas: str) -> str:
    """HTML mínimo con la sección #cheat y su tabla de "Modelo por defecto".

    Respeta la estructura que busca verificar_modelos: sección acotada por
    id="cheat" hasta el próximo <section, tabla cuyo <thead> dice "Modelo por
    defecto" y filas <tr><td>proveedor</td><td>modelo</td><td>LLAVE</td></tr>.
    """
    return (
        '<section id="cheat">'
        "<table><thead><tr><th>Proveedor</th>"
        "<th>Modelo por defecto</th><th>Llave</th></tr></thead>"
        f"<tbody>{filas}</tbody></table>"
        "</section>"
        '<section id="otra">fin</section>'
    )


@pytest.mark.offline
class TestVerificarModelos:
    def test_modelos_coinciden(self):
        """Si el HTML y el dict de modelos dicen lo mismo, el chequeo pasa."""
        modelos = {"google": "gemini-x", "openai": "gpt-y"}
        html = _html_cheat(
            "<tr><td>google</td><td>gemini-x</td><td>GOOGLE_API_KEY</td></tr>"
            "<tr><td>openai</td><td>gpt-y</td><td>OPENAI_API_KEY</td></tr>"
        )
        assert verificar_curso.verificar_modelos(html, modelos).ok is True

    def test_modelo_divergente_falla_y_nombra_ambos_valores(self):
        """Si el HTML trae otro modelo, el detalle nombra proveedor y ambos valores."""
        modelos = {"google": "gemini-x"}
        html = _html_cheat(
            "<tr><td>google</td><td>gemini-VIEJO</td><td>GOOGLE_API_KEY</td></tr>"
        )
        resultado = verificar_curso.verificar_modelos(html, modelos)
        assert resultado.ok is False
        detalle = " ".join(resultado.detalles)
        assert "google" in detalle
        assert "gemini-x" in detalle and "gemini-VIEJO" in detalle


# ------------------------------------------------------------------
# (d) verificar_tablas_modulos: #mapa (HTML) espeja la §5 del README
# ------------------------------------------------------------------
def _html_mapa(filas: str) -> str:
    """HTML mínimo con la sección #mapa y su tabla de módulos.

    verificar_tablas_modulos busca en #mapa una tabla cuyo <thead> contenga
    "Concepto" y un <tbody> con filas de 4 <td>: Concepto|Ejemplo|Ejercicio|Test.
    """
    return (
        '<section id="mapa">'
        "<table><thead><tr><th>Concepto</th><th>Ejemplo</th>"
        "<th>Ejercicio</th><th>Test</th></tr></thead>"
        f"<tbody>{filas}</tbody></table>"
        "</section>"
        '<section id="otra">fin</section>'
    )


# README con encabezado "## 5)" seguido de una tabla Markdown completa:
# cabecera + separador + filas de datos. La cabecera está a propósito para
# comprobar que NO se cuela como fila de datos (bug del extractor ya corregido).
_README_ESPEJADO = (
    "## 5) Mapa de módulos\n"
    "| Concepto | Ejemplo | Ejercicio | Test |\n"
    "|---|---|---|---|\n"
    "| Prompts | 02_prompts | ej-02 | test_prompts |\n"
    "| RAG | 11_rag | ej-11 | test_rag |\n"
)


@pytest.mark.offline
class TestVerificarTablasModulos:
    def test_tablas_espejadas_pasan_y_la_cabecera_no_cuenta(self):
        """Mismas filas en ambos lados → ok=True; la cabecera Markdown NO es una fila.

        Si el extractor contara la cabecera ('Concepto|Ejemplo|Ejercicio|Test')
        como fila de datos, aparecería una fila fantasma solo en el README y el
        chequeo fallaría. Que pase confirma que el bug quedó cerrado.
        """
        html = _html_mapa(
            "<tr><td>Prompts</td><td>02_prompts</td><td>ej-02</td><td>test_prompts</td></tr>"
            "<tr><td>RAG</td><td>11_rag</td><td>ej-11</td><td>test_rag</td></tr>"
        )
        assert verificar_curso.verificar_tablas_modulos(html, _README_ESPEJADO).ok is True

    def test_fila_que_falta_en_un_lado_falla(self):
        """Si al HTML le falta una fila que sí está en el README, el chequeo falla."""
        html = _html_mapa(
            "<tr><td>Prompts</td><td>02_prompts</td><td>ej-02</td><td>test_prompts</td></tr>"
        )
        resultado = verificar_curso.verificar_tablas_modulos(html, _README_ESPEJADO)
        assert resultado.ok is False

    def test_columna_ejercicio_se_excluye_de_la_comparacion(self):
        """La columna Ejercicio (índice 2) diverge a propósito y NO debe romper el espejo."""
        # Mismos Concepto/Ejemplo/Test que el README, pero con otro 'Ejercicio'.
        html = _html_mapa(
            "<tr><td>Prompts</td><td>02_prompts</td><td>OTRO-EJ</td><td>test_prompts</td></tr>"
            "<tr><td>RAG</td><td>11_rag</td><td>TAMBIEN-OTRO</td><td>test_rag</td></tr>"
        )
        assert verificar_curso.verificar_tablas_modulos(html, _README_ESPEJADO).ok is True


# ------------------------------------------------------------------
# Chequeos de la WEB: fixtures mínimas en memoria, sin tocar web/ real
# ------------------------------------------------------------------
# Un manifest de juguete con 2 rutas y 1 extra: suficiente para ejercitar
# order/total/disco, niveles y banners sin depender del contenido real.
def _manifest_mini() -> dict:
    return {
        "total": 3,
        "modules": [
            {"slug": "01-a", "order": 0, "level": 1, "levelName": "Uno", "pyFile": "01_a.py"},
            {"slug": "02-b", "order": 1, "level": 2, "levelName": "Dos", "pyFile": None},
        ],
        "extras": [{"slug": "faq"}],
    }


_MDX_COMPLETO = (
    "<LevelBanner level={1} title=\"Ruta 1\">abre</LevelBanner>\n"
    "prosa con [enlace](/concepto/02-b) y [otro](/recurso/faq#seccion)\n"
    "<Box kind=\"practice\">práctica</Box>\n"
    "<Checkpoint>listo</Checkpoint>\n"
    "<Quiz title=\"q\">…</Quiz>\n"
    "<Recap level={1}>cierre</Recap>\n"
)
_MDX_COMPLETO_2 = _MDX_COMPLETO.replace("level={1}", "level={2}")


@pytest.mark.offline
class TestVerificarManifest:
    def test_manifest_coherente_pasa(self):
        resultado = verificar_curso.verificar_manifest(
            _manifest_mini(), {"01-a", "02-b"}, {"faq"})
        assert resultado.ok is True

    def test_order_desincronizado_falla_y_nombra_el_slug(self):
        manifest = _manifest_mini()
        manifest["modules"][1]["order"] = 7  # la posición real es 1
        resultado = verificar_curso.verificar_manifest(manifest, {"01-a", "02-b"}, {"faq"})
        assert resultado.ok is False
        assert any("02-b" in d and "order=7" in d for d in resultado.detalles)

    def test_mdx_huerfano_y_faltante_fallan(self):
        # '03-c.mdx' sobra en disco y '02-b' no tiene archivo: dos fallos distintos.
        resultado = verificar_curso.verificar_manifest(
            _manifest_mini(), {"01-a", "03-c"}, {"faq"})
        assert resultado.ok is False
        assert any("02-b" in d for d in resultado.detalles)
        assert any("03-c" in d for d in resultado.detalles)


@pytest.mark.offline
class TestVerificarPyfiles:
    def test_pyfile_inexistente_falla(self):
        resultado = verificar_curso.verificar_pyfiles(
            _manifest_mini(), existe=lambda ruta: False)
        assert resultado.ok is False
        assert any("01_a.py" in d for d in resultado.detalles)

    def test_pyfile_null_no_se_exige(self):
        # Solo '01-a' referencia archivo; si existe, el chequeo pasa aunque
        # '02-b' tenga pyFile null (los módulos de lectura no prometen script).
        resultado = verificar_curso.verificar_pyfiles(
            _manifest_mini(), existe=lambda ruta: ruta == "01_a.py")
        assert resultado.ok is True


@pytest.mark.offline
class TestVerificarEnlacesWeb:
    def test_enlace_con_fragmento_resuelve_y_el_roto_falla(self):
        mdx = {"01-a": "ver [b](/concepto/02-b#anclado) y [x](/concepto/no-existe)"}
        resultado = verificar_curso.verificar_enlaces_web(mdx, {"01-a", "02-b"}, {"faq"})
        assert resultado.ok is False
        # El fragmento #anclado no rompe la resolución; el slug inventado sí.
        assert len(resultado.detalles) == 1
        assert "no-existe" in resultado.detalles[0]


@pytest.mark.offline
class TestVerificarNiveles:
    def test_niveles_correctos_pasan(self):
        mdx = {"01-a": _MDX_COMPLETO, "02-b": _MDX_COMPLETO_2}
        assert verificar_curso.verificar_niveles(_manifest_mini(), mdx).ok is True

    def test_recap_desincronizado_falla(self):
        mdx = {"01-a": _MDX_COMPLETO,
               "02-b": _MDX_COMPLETO_2.replace("<Recap level={2}", "<Recap level={5}")}
        resultado = verificar_curso.verificar_niveles(_manifest_mini(), mdx)
        assert resultado.ok is False
        assert any("Recap" in d and "5" in d for d in resultado.detalles)

    def test_ruta_sin_banner_de_apertura_falla(self):
        mdx = {"01-a": _MDX_COMPLETO,
               "02-b": _MDX_COMPLETO_2.replace("<LevelBanner level={2}", "<div ")}
        resultado = verificar_curso.verificar_niveles(_manifest_mini(), mdx)
        assert resultado.ok is False
        assert any("abre la ruta" in d for d in resultado.detalles)


@pytest.mark.offline
class TestVerificarMdx:
    def test_pauta_completa_y_trampa_en_codigo_no_cuentan(self):
        # El '<1.24' vive en un fence y el '`<5 s`' en inline code: ambos son
        # legales; solo el texto suelto puede romper el build.
        mdx = {"01-a": _MDX_COMPLETO + "```toml\nonnxruntime<1.24\n```\ntarda `<5 s` en frío\n"}
        assert verificar_curso.verificar_mdx(mdx).ok is True

    def test_trampa_fuera_de_codigo_falla_con_linea(self):
        mdx = {"01-a": _MDX_COMPLETO + "responde en <5 segundos\n"}
        resultado = verificar_curso.verificar_mdx(mdx)
        assert resultado.ok is False
        assert any("línea 7" in d for d in resultado.detalles)

    def test_modulo_sin_quiz_falla(self):
        mdx = {"01-a": _MDX_COMPLETO.replace("<Quiz", "<div")}
        resultado = verificar_curso.verificar_mdx(mdx)
        assert resultado.ok is False
        assert any("Quiz" in d for d in resultado.detalles)
