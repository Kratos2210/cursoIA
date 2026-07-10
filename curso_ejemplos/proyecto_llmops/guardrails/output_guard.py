"""
output_guard.py · La última red antes de que el usuario lea la respuesta
========================================================================
FINALIDAD:
  Revisar lo que el modelo produjo. El prompt ya le pidió que no filtrara nada,
  pero un LLM es un sistema probabilístico: obedece casi siempre. "Casi siempre"
  no es una garantía de seguridad, y en una financiera la diferencia entre
  99% y 100% se mide en multas.

  ⭐ Este módulo existe porque el prompt NO es un control de seguridad. Es una
     petición muy educada. El control es código determinista que corre después.

LÓGICA (tres capas, de la más grave a la más leve):
  1. TÉRMINOS SENSIBLES → redactar ([REDACTED]). Una llave de API o un DSN de
     Postgres en la respuesta significa que algo del entorno se coló en el
     contexto. Se tapa y se marca.
  2. PII                → anonimizar ([DNI], [EMAIL]…). El contexto recuperado
     podía traer datos de clientes; que sean relevantes no los hace publicables.
  3. FUGA DE NIVEL      → bloquear. Si la respuesta cita material 'restricted' y
     quien pregunta no tiene ese nivel, el RBAC falló aguas arriba. Aquí se corta.

  Las capas 1 y 2 SANEAN (la respuesta llega, tapada). La capa 3 BLOQUEA: cuando
  se ha filtrado material de un nivel superior no basta con tapar palabras — no
  sabemos qué más se parafraseó.

⚠️ La capa 3 es defensa en profundidad, no la defensa principal. Lo correcto es
   que `guardrails/rbac.py` no le entregue jamás al modelo un documento que el
   rol no puede ver. Si esta capa salta en producción, hay un bug arriba y lo que
   toca es arreglarlo, no subir el umbral de aquí.
"""
from __future__ import annotations

from guardrails import pii, policy, rbac
from guardrails.policy import ResultadoGuard

# Frases que delatan que la respuesta se apoya en material restringido. Vienen
# de los anexos (normativa_anexo.txt): son literales del texto confidencial.
#
# Es una heurística de "canario", no un detector semántico: si el modelo
# parafrasea el anexo sin usar estas palabras, no salta. Por eso el RBAC de
# arriba es la defensa de verdad y esto solo la respalda.
_CANARIOS_RESTRINGIDOS: tuple[str, ...] = (
    "clave maestra", "claves maestras", "hsm", "no divulgar",
)


def revisar_salida(texto: str, rol: str = "analyst") -> ResultadoGuard:
    """Sanea la respuesta del modelo. FUNCIÓN PURA → testeable sin LLM.

    Devuelve un ResultadoGuard:
      - permitido=False → hubo fuga de nivel; se responde un mensaje genérico.
      - permitido=True  → devuelve `resultado.texto`, YA saneado. Nunca el original.

    Parámetro:
      rol: el rol de quien preguntó. Decide si citar material restringido es una
           fuga (un 'analyst') o algo perfectamente legítimo (un 'compliance').
    """
    acciones: list[str] = []
    resultado = texto

    # ---- 1) Términos sensibles: credenciales, DSNs, contraseñas -------------
    encontrados = policy.terminos_sensibles_en(resultado)
    if encontrados:
        resultado = policy.filtra_salida(resultado)
        acciones.append("terminos_redactados")

    # ---- 2) PII: datos de clientes que venían en el contexto ----------------
    if pii.contiene_pii(resultado):
        resultado = pii.anonimizar(resultado)
        acciones.append("pii_anonimizada")

    # ---- 3) Fuga de nivel: el RBAC de arriba dejó pasar algo ----------------
    if _hay_fuga_de_nivel(resultado, rol):
        return ResultadoGuard(
            permitido=False,
            texto="No tengo autorización para responder eso con tu nivel de acceso.",
            motivo=f"La respuesta cita material restringido y el rol '{rol}' no puede verlo.",
            acciones=(*acciones, "bloqueo_fuga_nivel"),
        )

    return ResultadoGuard(permitido=True, texto=resultado, acciones=tuple(acciones))


def _hay_fuga_de_nivel(texto: str, rol: str) -> bool:
    """¿Cita la respuesta material que este rol no debería haber visto?

    Reutiliza la jerarquía de `rbac.niveles_permitidos()`: la política de quién
    ve qué está definida en UN solo sitio. Si mañana se añade un rol, este
    guardrail lo entiende sin tocarlo.
    """
    if "restricted" in rbac.niveles_permitidos(rol):
        return False        # el rol puede verlo: citarlo no es una fuga
    t = texto.lower()
    return any(canario in t for canario in _CANARIOS_RESTRINGIDOS)
