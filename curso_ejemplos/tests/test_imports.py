"""
test_imports.py · Smoke test: ¿todos los ejemplos siguen cargando?
==================================================================
FINALIDAD:
  El test más barato y más rentable del curso. Recorre TODOS los archivos
  'NN_*.py' y los importa. Con eso detecta, sin gastar un token:

    - un import que desapareció al subir de versión (langchain 1.3 -> 1.4),
    - un error de sintaxis,
    - una función que se movió de sitio,
    - un ejemplo que hace trabajo pesado al importarse (ver más abajo).

LÓGICA:
  Importar un ejemplo NO ejecuta su main(): todos están protegidos con
  'if __name__ == "__main__"'. Esa protección es justamente lo que este
  test blinda: si alguien deja una llamada a la API en el cuerpo del
  módulo, importarlo intentaría hablar con Gemini y el test fallaría
  (o pediría una llave que en la CI no existe).

Ejecuta:  uv run pytest curso_ejemplos/tests/test_imports.py -v
"""
import re

import pytest

pytestmark = pytest.mark.offline

# Nombre de ejemplo del curso: '07_herramientas.py', '13b_human_in_the_loop.py'…
PATRON_EJEMPLO = re.compile(r"^\d{2}[a-z]?_.+\.py$")


def _ejemplos(carpeta):
    """Todos los ejemplos numerados, ordenados por nombre."""
    return sorted(p for p in carpeta.glob("*.py") if PATRON_EJEMPLO.match(p.name))


def test_hay_ejemplos_que_probar(carpeta_curso):
    """Red de seguridad del propio test: si el glob deja de encontrar nada,
    los tests de abajo pasarían 'en vacío' y no nos enteraríamos."""
    assert len(_ejemplos(carpeta_curso)) >= 14


def test_todos_los_ejemplos_se_importan(carpeta_curso, importar_ejemplo):
    """Importa uno por uno cada ejemplo del curso.

    Si esto falla tras un 'uv sync', casi siempre es una librería que
    cambió de API. El mensaje de error te dice cuál.
    """
    fallos = []
    for ruta in _ejemplos(carpeta_curso):
        try:
            importar_ejemplo(ruta.stem)
        except Exception as error:  # noqa: BLE001 — queremos reportarlos TODOS
            fallos.append(f"{ruta.name}: {type(error).__name__}: {error}")
    assert not fallos, "ejemplos que no se pudieron importar:\n" + "\n".join(fallos)


def test_ningun_ejemplo_necesita_la_llave_para_importarse(carpeta_curso, importar_ejemplo, monkeypatch):
    """Sin GOOGLE_API_KEY, importar un ejemplo debe seguir funcionando.

    Es la garantía de que la CI (que no tiene llave) puede correr, y de que
    la validación de la llave vive DENTRO de main(), no en el cuerpo del módulo.
    """
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    for ruta in _ejemplos(carpeta_curso):
        importar_ejemplo(ruta.stem)


def test_cada_ejemplo_tiene_main_y_docstring(carpeta_curso, importar_ejemplo):
    """El estilo del curso: cada ejemplo se explica y se ejecuta desde main()."""
    sin_main, sin_doc = [], []
    for ruta in _ejemplos(carpeta_curso):
        modulo = importar_ejemplo(ruta.stem)
        if not callable(getattr(modulo, "main", None)):
            sin_main.append(ruta.name)
        if not (modulo.__doc__ or "").strip():
            sin_doc.append(ruta.name)
    assert not sin_main, f"ejemplos sin main(): {sin_main}"
    assert not sin_doc, f"ejemplos sin docstring explicativo: {sin_doc}"


def test_util_se_importa(carpeta_curso):
    """util.py es la base compartida: si se rompe, se rompe todo lo demás."""
    import util
    assert callable(util.trocear_parrafos)
