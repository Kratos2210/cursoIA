"""
rbac.py · Control de acceso por rol, a nivel de documento
==========================================================
FINALIDAD:
  Decidir QUIÉN puede ver QUÉ. El RAG recupera por parecido semántico; eso no
  sabe nada de permisos. Un fragmento sobre las claves maestras del HSM es
  perfectamente relevante para "¿cómo se protegen las claves?" — y precisamente
  por eso hay que quitárselo a quien no tiene autorización.

  ⭐ La regla de oro: **recuperar y autorizar son dos pasos distintos**.
     Primero se busca, después se filtra. Nunca al revés, y nunca a la vez.

LÓGICA:
  - Cada fragmento lleva `metadata['confidentiality']` (lo pone app/rag.py).
  - Cada rol tiene un conjunto de niveles que puede ver (JERARQUIA_ROL).
  - filtrar_por_rol() aplica la intersección. Es una función PURA: sin red,
    sin base de datos, sin modelo. Por eso se testea gratis y en milisegundos.

⚠️ Esto es autorización a nivel de DOCUMENTO, no de campo. Si un mismo párrafo
   mezcla datos públicos y restringidos, este filtro no basta: hay que trocear
   mejor, o anonimizar (ver guardrails/pii.py).
"""
from __future__ import annotations

from langchain_core.documents import Document

# Los tres niveles, de menos a más sensible.
NIVELES_CONFIDENCIALIDAD = ("public", "internal", "restricted")

# Qué ve cada rol. Es acumulativo: quien ve 'internal' también ve 'public'.
#   public     → cualquiera (una web, un cliente)
#   analyst    → el analista de datos: la normativa interna completa
#   compliance → oficial de cumplimiento: además, los anexos restringidos
JERARQUIA_ROL = {
    "public": {"public"},
    "analyst": {"public", "internal"},
    "compliance": {"public", "internal", "restricted"},
}

# El nivel que se asume cuando un documento no trae etiqueta. Elegimos el MÁS
# restrictivo a propósito: ante la duda, no enseñar. Un fallo de clasificación
# debe negar el acceso, nunca concederlo.
NIVEL_POR_DEFECTO = "restricted"


def niveles_permitidos(rol: str) -> set[str]:
    """Qué niveles de confidencialidad puede ver un rol.

    Un rol desconocido cae al mínimo privilegio ('public'), no al máximo.
    """
    return JERARQUIA_ROL.get(rol, JERARQUIA_ROL["public"])


def filtrar_por_rol(docs: list[Document], rol: str) -> list[Document]:
    """Quita los documentos que el rol no puede ver. FUNCIÓN PURA.

    El corazón del RBAC: el retriever trae por similitud; la autorización se
    aplica DESPUÉS, aquí, sobre lo que trajo.
    """
    permitidos = niveles_permitidos(rol)
    return [
        d for d in docs
        if d.metadata.get("confidentiality", NIVEL_POR_DEFECTO) in permitidos
    ]
