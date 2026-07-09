"""
test_audit.py · El molde del hallazgo y el rastro de auditoría
==============================================================
En una financiera esto es lo MÁS importante que hay que testear: si el log
de auditoría miente, se pierde o se sobrescribe, el proyecto no sirve —
por muy bien que converse el agente.
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

import audit

pytestmark = pytest.mark.offline

MOMENTO = datetime(2026, 7, 9, 14, 30, 5)


# ==================================================================
# El molde Pydantic
# ==================================================================
class TestHallazgoCalidad:
    def test_hallazgo_valido(self):
        h = audit.HallazgoCalidad(regla="R", cumple=True, severidad="alta", justificacion="J")
        assert h.cumple is True and h.severidad == "alta"

    @pytest.mark.parametrize("entrada,esperado", [
        ("ALTA", "alta"),      # el modelo grita
        (" Media ", "media"),  # el modelo deja espacios
        ("Baja", "baja"),      # el modelo capitaliza
    ])
    def test_normaliza_la_severidad(self, entrada, esperado):
        """El LLM no es consistente con mayúsculas: normalizamos al recibir."""
        h = audit.HallazgoCalidad(regla="R", cumple=True, severidad=entrada, justificacion="J")
        assert h.severidad == esperado

    def test_rechaza_una_severidad_inventada(self):
        """'crítica' no está en nuestra escala. Falla aquí, no en el log."""
        with pytest.raises(ValidationError):
            audit.HallazgoCalidad(regla="R", cumple=True, severidad="crítica", justificacion="J")

    def test_todos_los_campos_son_obligatorios(self):
        with pytest.raises(ValidationError):
            audit.HallazgoCalidad(regla="R", cumple=True)

    def test_cada_campo_lleva_description(self):
        """Los 'description' son las instrucciones que lee el modelo al rellenar."""
        for campo in audit.HallazgoCalidad.model_fields.values():
            assert campo.description


# ==================================================================
# formatear_linea: función pura -> línea exacta
# ==================================================================
class TestFormatearLinea:
    def test_la_linea_exacta(self, hallazgo_ejemplo):
        linea = audit.formatear_linea(hallazgo_ejemplo, MOMENTO)
        assert linea == (
            "2026-07-09 14:30:05 | cumple=True | severidad=alta | "
            "Los datos personales deben cifrarse en reposo con AES-256"
        )

    def test_aplana_los_saltos_de_linea_de_la_regla(self):
        """UNA línea del archivo = UN hallazgo. Si no, el log no es parseable."""
        h = audit.HallazgoCalidad(regla="regla\ncon\nsaltos", cumple=False,
                                  severidad="baja", justificacion="J")
        linea = audit.formatear_linea(h, MOMENTO)
        assert "\n" not in linea
        assert linea.endswith("regla con saltos")

    def test_registra_el_incumplimiento(self):
        h = audit.HallazgoCalidad(regla="R", cumple=False, severidad="alta", justificacion="J")
        assert "cumple=False" in audit.formatear_linea(h, MOMENTO)

    def test_es_pura(self, hallazgo_ejemplo):
        """Mismo hallazgo + mismo momento -> misma línea, siempre."""
        a = audit.formatear_linea(hallazgo_ejemplo, MOMENTO)
        b = audit.formatear_linea(hallazgo_ejemplo, MOMENTO)
        assert a == b


# ==================================================================
# registrar_auditoria: el efecto sobre el disco
# ==================================================================
class TestRegistrarAuditoria:
    def test_escribe_una_linea_en_el_log(self, hallazgo_ejemplo, ruta_log):
        audit.registrar_auditoria(hallazgo_ejemplo, ruta=ruta_log, momento=MOMENTO)
        assert ruta_log.read_text(encoding="utf-8").splitlines() == [
            audit.formatear_linea(hallazgo_ejemplo, MOMENTO)
        ]

    def test_crea_el_archivo_si_no_existe(self, hallazgo_ejemplo, ruta_log):
        assert not ruta_log.exists()
        audit.registrar_auditoria(hallazgo_ejemplo, ruta=ruta_log)
        assert ruta_log.exists()

    def test_nunca_sobrescribe_lo_ya_auditado(self, hallazgo_ejemplo, ruta_log):
        """Modo 'append'. Un log que se pisa es evidencia destruida.

        Este es EL test del módulo: si alguien cambia "a" por "w", se pone rojo.
        """
        for _ in range(3):
            audit.registrar_auditoria(hallazgo_ejemplo, ruta=ruta_log)
        assert len(audit.leer_auditoria(ruta_log)) == 3

    def test_devuelve_la_linea_escrita(self, hallazgo_ejemplo, ruta_log):
        linea = audit.registrar_auditoria(hallazgo_ejemplo, ruta=ruta_log, momento=MOMENTO)
        assert linea in ruta_log.read_text(encoding="utf-8")


# ==================================================================
# leer_auditoria
# ==================================================================
class TestLeerAuditoria:
    def test_log_inexistente_devuelve_lista_vacia(self, ruta_log):
        """Primera ejecución del proyecto: aún no hay log. No debe reventar."""
        assert audit.leer_auditoria(ruta_log) == []

    def test_devuelve_las_lineas_en_orden(self, ruta_log):
        h1 = audit.HallazgoCalidad(regla="primera", cumple=True, severidad="baja", justificacion="J")
        h2 = audit.HallazgoCalidad(regla="segunda", cumple=False, severidad="alta", justificacion="J")
        audit.registrar_auditoria(h1, ruta=ruta_log)
        audit.registrar_auditoria(h2, ruta=ruta_log)
        lineas = audit.leer_auditoria(ruta_log)
        assert lineas[0].endswith("primera")
        assert lineas[1].endswith("segunda")

    def test_ignora_lineas_en_blanco(self, ruta_log):
        ruta_log.write_text("una linea\n\n\n", encoding="utf-8")
        assert audit.leer_auditoria(ruta_log) == ["una linea"]
