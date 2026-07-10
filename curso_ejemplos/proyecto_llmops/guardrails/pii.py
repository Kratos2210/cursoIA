"""
pii.py · Detección y anonimización de datos personales
=======================================================
FINALIDAD:
  Encontrar PII (Personally Identifiable Information) en un texto y taparla.
  Se usa en los DOS extremos del servicio:

    - a la ENTRADA: el usuario pega un DNI en su pregunta. Ese DNI viajaría al
      proveedor del modelo y quedaría en sus logs. Lo anonimizamos antes.
    - a la SALIDA:  el modelo repite un número de tarjeta que estaba en el
      contexto recuperado. Lo tapamos antes de devolverlo.

  ⭐ El orden importa: anonimizar a la entrada protege al TITULAR del dato;
     anonimizar a la salida protege contra la FUGA. Son dos riesgos distintos y
     hacen falta los dos.

LÓGICA (regex first, y por qué):
  Empezamos con expresiones regulares, no con un modelo. Motivos:
    1) son deterministas → la misma entrada da siempre el mismo resultado,
    2) son gratis y no salen de esta máquina (un detector de PII que llama a una
       API para analizar PII es un contrasentido),
    3) se testean en milisegundos.

  El coste: los regex tienen falsos positivos. Un "12345678" puede ser un DNI o
  un identificador de factura. Por eso:
    - la tarjeta se valida con el algoritmo de **Luhn** (no basta con 16 dígitos),
    - el RUC se comprueba antes que el DNI (11 dígitos antes que 8),
    - se exigen fronteras de palabra (\\b) para no partir números más largos.

  ⭐ El escalón siguiente es Microsoft **Presidio** (NER + reglas). Se deja como
     extra opcional: pesa cientos de MB y arrastra spaCy. La INTERFAZ de este
     módulo (`detectar`, `anonimizar`) es la que Presidio implementaría, así que
     cambiar de motor no obliga a tocar los guardrails que lo usan.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ------------------------------------------------------------------
# 1) LOS PATRONES
# ------------------------------------------------------------------
# Cada entrada: (tipo, regex). El ORDEN es significativo — ver detectar().
#
# \b es una "frontera de palabra": impide que el patrón de DNI (8 dígitos)
# muerda los 8 primeros dígitos de un número de tarjeta de 16.
_PATRONES: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Email: deliberadamente laxo. Un email mal formado sigue siendo PII.
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),

    # Tarjeta de crédito: 13-19 dígitos, opcionalmente en grupos separados por
    # espacio o guion. El regex solo PROPONE; Luhn confirma (ver detectar()).
    ("tarjeta", re.compile(r"\b(?:\d[ -]?){12,18}\d\b")),

    # RUC peruano: 11 dígitos que empiezan por 10 (persona natural),
    # 15, 17 o 20 (persona jurídica). Va ANTES que el DNI: comparten dígitos.
    ("ruc", re.compile(r"\b(?:10|15|17|20)\d{9}\b")),

    # DNI peruano: exactamente 8 dígitos.
    ("dni", re.compile(r"\b\d{8}\b")),

    # Teléfono móvil peruano: 9 dígitos que empiezan por 9, con prefijo opcional.
    ("telefono", re.compile(r"\b(?:\+51[ -]?)?9\d{8}\b")),
)

# Con qué se sustituye cada tipo. La marca es VISIBLE a propósito: quien lee la
# respuesta debe saber que hubo una redacción, no creer que el dato no existía.
_MASCARAS = {
    "email": "[EMAIL]",
    "tarjeta": "[TARJETA]",
    "ruc": "[RUC]",
    "dni": "[DNI]",
    "telefono": "[TELEFONO]",
}


@dataclass(frozen=True)
class Deteccion:
    """Un dato personal encontrado: qué es, cuál es, y dónde estaba.

    Guardamos las posiciones (inicio, fin) porque anonimizar bien exige
    reemplazar de derecha a izquierda: si sustituyes de izquierda a derecha, la
    primera máscara desplaza todos los índices siguientes.
    """
    tipo: str
    valor: str
    inicio: int
    fin: int


# ------------------------------------------------------------------
# 2) LUHN — la validación que quita los falsos positivos
# ------------------------------------------------------------------
def es_luhn_valido(digitos: str) -> bool:
    """¿Pasa esta cadena de dígitos el checksum de Luhn?

    Luhn es el algoritmo con el que se validan las tarjetas de crédito desde
    los años 60. Recorre los dígitos de DERECHA a izquierda y duplica uno de
    cada dos; si el doble pasa de 9, le resta 9. La tarjeta es válida si la suma
    total es múltiplo de 10.

    Sin esto, cualquier número de 16 dígitos (un ID de transacción, un timestamp
    en nanosegundos) se marcaría como tarjeta. Es una FUNCIÓN PURA.
    """
    solo_digitos = [int(c) for c in digitos if c.isdigit()]
    if len(solo_digitos) < 13:
        return False

    suma = 0
    # [::-1] invierte: Luhn se calcula desde el último dígito.
    for posicion, digito in enumerate(reversed(solo_digitos)):
        if posicion % 2 == 1:          # las posiciones impares se duplican
            digito *= 2
            if digito > 9:
                digito -= 9
        suma += digito
    return suma % 10 == 0


# ------------------------------------------------------------------
# 3) DETECCIÓN
# ------------------------------------------------------------------
def detectar(texto: str) -> list[Deteccion]:
    """Todos los datos personales del texto, ordenados por posición.

    Estrategia contra el solapamiento: los patrones se prueban en el orden de
    _PATRONES (del más específico al más genérico) y se marca como "ocupado"
    cada tramo ya reclamado. Así los 16 dígitos de una tarjeta no vuelven a
    contarse como un DNI de 8.

    La tarjeta es el único tipo con validación extra: si no pasa Luhn, el tramo
    NO se reclama y queda libre para que lo miren los patrones siguientes.
    """
    detecciones: list[Deteccion] = []
    ocupados: list[tuple[int, int]] = []

    def _se_solapa(inicio: int, fin: int) -> bool:
        return any(inicio < f and i < fin for i, f in ocupados)

    for tipo, patron in _PATRONES:
        for coincidencia in patron.finditer(texto):
            inicio, fin = coincidencia.span()
            if _se_solapa(inicio, fin):
                continue
            valor = coincidencia.group()

            # Una "tarjeta" que no pasa Luhn casi nunca es una tarjeta.
            if tipo == "tarjeta" and not es_luhn_valido(valor):
                continue

            detecciones.append(Deteccion(tipo, valor, inicio, fin))
            ocupados.append((inicio, fin))

    return sorted(detecciones, key=lambda d: d.inicio)


def contiene_pii(texto: str) -> bool:
    """¿Hay algún dato personal aquí? El atajo booleano de detectar()."""
    return bool(detectar(texto))


# ------------------------------------------------------------------
# 4) ANONIMIZACIÓN
# ------------------------------------------------------------------
def anonimizar(texto: str) -> str:
    """Sustituye cada PII por su máscara. El resto del texto no se toca.

    ⭐ Se recorre en orden INVERSO (de la última detección a la primera). Si lo
       hiciéramos al derecho, reemplazar '12345678' por '[DNI]' movería todas
       las posiciones posteriores y las siguientes sustituciones cortarían mal.
    """
    resultado = texto
    for deteccion in reversed(detectar(texto)):
        mascara = _MASCARAS[deteccion.tipo]
        resultado = resultado[:deteccion.inicio] + mascara + resultado[deteccion.fin:]
    return resultado


def resumen(texto: str) -> dict[str, int]:
    """Cuántos datos de cada tipo hay. Para las métricas y la auditoría.

    Nos interesa saber CUÁNTA PII pasa por el servicio (¿la gente pega DNIs en
    el chat?) sin registrar NUNCA el valor concreto. Por eso devuelve conteos,
    no valores: un log de PII sería, él mismo, una fuga de PII.
    """
    conteo: dict[str, int] = {}
    for deteccion in detectar(texto):
        conteo[deteccion.tipo] = conteo.get(deteccion.tipo, 0) + 1
    return conteo
