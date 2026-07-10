"""
test_streaming.py · El guardrail que sobrevive al streaming
============================================================
`GuardiaDeStream` es una máquina de estados PURA: se le empujan strings y
devuelve strings. Ni modelo, ni red. Por eso se puede probar de verdad el caso
que más cuesta razonar: **un término sensible partido entre dos tokens**.

El invariante que sostiene el módulo — `VENTANA >= el patrón más largo` — tiene
su propio test. Si alguien añade a policy.py un término de 80 caracteres, esa
prueba falla y avisa; sin ella, el streaming dejaría de filtrar en silencio.
"""
import json

import pytest

from app import streaming
from app.streaming import GuardiaDeStream

pytestmark = pytest.mark.offline


def _consumir(guardia: GuardiaDeStream, tokens: list[str]) -> str:
    """Empuja todos los tokens y devuelve lo que llegó al usuario."""
    salida = ""
    for token in tokens:
        salida += guardia.empujar(token)
        if guardia.bloqueado:
            return salida
    return salida + guardia.cerrar()


class TestInvariante:
    def test_la_ventana_cubre_el_patron_mas_largo(self):
        # ⭐ Si esto falla, el buffer de retención ya no garantiza que un término
        #    sensible quepa entero dentro de la cola: podría partirse y colarse.
        assert streaming.VENTANA >= streaming.longitud_maxima_de_patron()


class TestTextoLimpio:
    def test_una_respuesta_limpia_llega_entera(self):
        tokens = ["La ", "Regla 1 ", "exige ", "AES-256."]
        assert _consumir(GuardiaDeStream(), tokens) == "La Regla 1 exige AES-256."

    def test_no_se_emite_nada_hasta_llenar_la_ventana(self):
        # El precio del buffer: los primeros VENTANA caracteres se retienen.
        guardia = GuardiaDeStream()
        assert guardia.empujar("hola") == ""

    def test_cerrar_vacia_la_cola_retenida(self):
        guardia = GuardiaDeStream()
        guardia.empujar("hola")
        assert guardia.cerrar() == "hola"


class TestTerminoPartidoEntreTokens:
    """El caso que un filtro token-a-token NO puede resolver."""

    def test_una_credencial_partida_se_redacta_igual(self):
        # 'api_key' llega en tres trozos: "ap" + "i_k" + "ey". Ningún token
        # contiene el término, pero el texto acumulado sí.
        relleno = "x" * 100          # empuja el término fuera de la ventana
        tokens = ["ap", "i_k", "ey", "=sk-123 ", relleno]
        salida = _consumir(GuardiaDeStream(), tokens)
        assert "api_key" not in salida
        assert "[REDACTED]" in salida

    def test_un_dni_partido_se_anonimiza_igual(self):
        tokens = ["El DNI 456", "789", "12 incumple. ", "y" * 100]
        salida = _consumir(GuardiaDeStream(), tokens)
        assert "45678912" not in salida
        assert "[DNI]" in salida


class TestFugaDeNivel:
    """Un canario restringido NUNCA debe llegar al usuario, ni un carácter."""

    def test_bloquea_antes_de_emitir_el_canario(self):
        # 'clave maestra' se completa dentro de la ventana retenida: cuando el
        # guardia lo detecta, todavía no ha salido ni una letra de él.
        tokens = ["Según el anexo, la ", "clave ", "maestra ", "vive en el HSM."]
        guardia = GuardiaDeStream(rol="analyst")
        salida = _consumir(guardia, tokens)
        assert guardia.bloqueado is True
        assert "clave" not in salida.lower()
        assert "hsm" not in salida.lower()

    def test_lo_ya_emitido_era_inofensivo(self):
        # Se retienen VENTANA caracteres, así que el prefijo que sí salió está
        # a más de VENTANA caracteres del canario: no puede contenerlo.
        relleno = "Contexto normativo general. " * 5
        guardia = GuardiaDeStream(rol="analyst")
        salida = _consumir(guardia, [relleno, "La clave maestra está en el HSM."])
        assert guardia.bloqueado is True
        assert salida.startswith("Contexto normativo general.")
        assert "maestra" not in salida

    def test_compliance_recibe_el_mismo_texto_sin_bloqueo(self):
        tokens = ["La clave maestra vive en el HSM.", " " + "z" * 100]
        guardia = GuardiaDeStream(rol="compliance")
        salida = _consumir(guardia, tokens)
        assert guardia.bloqueado is False
        assert "clave maestra" in salida

    def test_un_canario_en_la_ultima_cola_tambien_bloquea(self):
        # El canario cae dentro de la ventana y nunca se emite: solo `cerrar()`
        # llega a verlo. Ese camino también tiene que bloquear.
        guardia = GuardiaDeStream(rol="analyst")
        _consumir(guardia, ["Todo bien. La clave maestra."])
        assert guardia.bloqueado is True

    def test_bloqueado_ignora_los_tokens_siguientes(self):
        guardia = GuardiaDeStream(rol="analyst")
        _consumir(guardia, ["La clave maestra."])
        assert guardia.empujar(" más texto") == ""
        assert guardia.cerrar() == ""


class TestTextoCompleto:
    def test_es_el_texto_saneado_lo_que_se_cachea(self):
        # ⭐ Cachear el texto crudo serviría, en el siguiente HIT, la respuesta
        #    sin filtrar: el guardrail correría una vez y se esquivaría siempre.
        guardia = GuardiaDeStream()
        _consumir(guardia, ["Usa api_key=sk-1 ", "x" * 100])
        assert "api_key" not in guardia.texto_completo
        assert "[REDACTED]" in guardia.texto_completo


class TestFormatoSSE:
    def test_termina_en_linea_en_blanco(self):
        # La línea en blanco no es estilo: es el delimitador del protocolo.
        # Sin ella el navegador espera para siempre.
        assert streaming.evento_sse({"token": "hola"}).endswith("\n\n")

    def test_incluye_el_nombre_del_evento_si_se_da(self):
        crudo = streaming.evento_sse({"error": "no"}, evento="bloqueado")
        assert crudo.startswith("event: bloqueado\n")

    def test_sin_evento_solo_hay_data(self):
        assert streaming.evento_sse({"a": 1}) == 'data: {"a": 1}\n\n'

    def test_no_escapa_los_acentos(self):
        # ensure_ascii=False: la normativa está en español y 'ó' no se lee.
        crudo = streaming.evento_sse({"token": "auditoría"})
        assert "auditoría" in crudo
        assert json.loads(crudo.split("data: ", 1)[1])["token"] == "auditoría"
