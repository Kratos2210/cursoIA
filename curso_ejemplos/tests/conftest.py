"""
conftest.py · Fixtures y utilidades compartidas por los tests
==============================================================
FINALIDAD:
  Centralizar lo que los tests necesitan una y otra vez:
    - La ruta a la carpeta del curso (donde están los ejemplos y datos_rag.txt).
    - El contenido de datos_rag.txt (el documento de RAG del TEMA 11/12).
    - importar_ejemplo(nombre): cargar un archivo 'NN_*.py' como módulo,
      aunque su nombre empiece por un número (Python no permite eso normalmente).

  Por qué importar_ejemplo: los archivos del curso se llaman '01_primer_modelo.py',
  etc. Un nombre que empieza con número NO se puede importar con 'import 01_...'.
  Usamos importlib para cargarlos a mano y poder testear sus funciones/constantes.
"""
import os
import sys
import importlib.util
from pathlib import Path
import pytest

# ---- La carpeta raíz del curso (un nivel arriba de tests/) ----
CARPETA_CURSO = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------
# Fixtures: datos de prueba
# ------------------------------------------------------------------
@pytest.fixture(scope="session")
def carpeta_curso() -> Path:
    """La carpeta que contiene todos los ejemplos del curso."""
    return CARPETA_CURSO


@pytest.fixture(scope="session")
def ruta_datos_rag() -> Path:
    """Ruta a datos_rag.txt (el documento usado en RAG)."""
    return CARPETA_CURSO / "datos_rag.txt"


@pytest.fixture(scope="session")
def texto_datos_rag(ruta_datos_rag) -> str:
    """El contenido completo de datos_rag.txt como string."""
    return ruta_datos_rag.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def chunks_datos_rag(texto_datos_rag) -> list[str]:
    """datos_rag.txt troceado por párrafo (7 fragmentos esperados)."""
    from util import trocear_parrafos
    return trocear_parrafos(texto_datos_rag)


# ------------------------------------------------------------------
# Helper: importar ejemplos cuyo nombre empieza con número
# ------------------------------------------------------------------
@pytest.fixture(scope="session")
def importar_ejemplo():
    """Devuelve una función cargar('11_rag') -> módulo Python.

    Uso en un test:
        modulo = importar_ejemplo("07_herramientas")
        assert modulo.calculadora_descuentos(3500, 18) == 2870.0
    """
    # Aseguramos que 'util' se pueda importar (añadimos la carpeta del curso).
    if str(CARPETA_CURSO) not in sys.path:
        sys.path.insert(0, str(CARPETA_CURSO))

    def _cargar(nombre_sin_py: str):
        ruta = CARPETA_CURSO / f"{nombre_sin_py}.py"
        if not ruta.exists():
            pytest.skip(f"no existe el ejemplo {ruta}")
        # Cargamos el archivo como módulo con un nombre seguro (sin dígitos).
        spec = importlib.util.spec_from_file_location(f"ej_{nombre_sin_py}", ruta)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo

    return _cargar
