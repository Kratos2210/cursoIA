"""
test_audit_import.py · El puente al molde del prototipo
========================================================
FINALIDAD:
  Comprobar que NO duplicamos `HallazgoCalidad` y que el puente es realmente
  perezoso. Su docstring decía "se importa perezosamente" mientras el código
  lo cargaba en tiempo de import: un comentario que miente es peor que ninguno.
"""
import sys

import pytest

pytestmark = pytest.mark.offline


def test_es_la_misma_clase_del_prototipo():
    """No es una copia con el mismo nombre: es EL molde de proyecto_final."""
    from app.audit_import import HallazgoCalidad
    from app._proyecto_final import audit

    assert HallazgoCalidad is audit.HallazgoCalidad


def test_el_validador_de_severidad_viaja_con_el_molde():
    """Si reutilizamos el molde, heredamos sus reglas de validación."""
    from pydantic import ValidationError

    from app.audit_import import HallazgoCalidad

    with pytest.raises(ValidationError):
        HallazgoCalidad(regla="x", cumple=True, severidad="urgentísima", justificacion="y")


def test_importar_el_modulo_no_carga_el_prototipo():
    """Perezoso de verdad: el coste se paga al USAR el símbolo, no al importarlo."""
    for modulo in ("app.audit_import", "app._proyecto_final", "audit"):
        sys.modules.pop(modulo, None)

    import app.audit_import as ai
    assert "app._proyecto_final" not in sys.modules, "el puente se cargó demasiado pronto"

    ai.HallazgoCalidad                       # ahora sí: primer acceso
    assert "app._proyecto_final" in sys.modules


def test_un_atributo_inexistente_falla_como_debe():
    import app.audit_import as ai

    with pytest.raises(AttributeError):
        ai.NoExisto


def test_expone_tambien_las_funciones_de_auditoria():
    from app import audit_import

    assert callable(audit_import.registrar_auditoria)
    assert callable(audit_import.leer_auditoria)
