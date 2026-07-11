"""
search.py · El presupuesto es un WHERE, no una preferencia
===========================================================
FINALIDAD:
  Los k productos que CUMPLEN los filtros de la petición. Puede devolver menos, o
  nada — y "nada" es una respuesta válida.

LÓGICA — dos fases, y el orden es el diseño:
  1. FILTROS DUROS (stock, presupuesto, categoría): un producto de S/39.90 ante
     un tope de S/25 no es "menos relevante", es INVÁLIDO. Eso lo resuelve un
     filtro (el WHERE del m24), jamás el ranking.
  2. RANKING por afinidad, SOLO entre los válidos: el color pedido pesa; a
     igualdad, gana el más barato (regla de la casa: primero lo accesible).

  ⭐ Y la regla del m20: si nada cumple → LISTA VACÍA. "No tengo" es honesto; un
     sustituto fuera de presupuesto no lo es.

⭐ ESCALABILIDAD (lo que este módulo deja preparado): hoy el ranking es solape de
   términos (el espíritu del m11 en miniatura). La función `afinidad` está
   aislada a propósito: cambiarla por embeddings + re-ranking (m12) o un índice
   vectorial (m24) no toca los filtros duros ni el resto del pipeline. Ver
   docs/adr/0005-escalabilidad-embeddings-vector-db.md.
"""
from __future__ import annotations


def buscar_productos(filtros: dict, catalogo: list[dict], k: int = 3) -> list[dict]:
    """Los k mejores productos que cumplen los filtros. FUNCIÓN PURA.

    filtros: {"presupuesto": float|None, "categoria": str|None, "color": str|None}
    """
    candidatos = [p for p in catalogo if p["disponible"]]
    if filtros.get("presupuesto") is not None:
        candidatos = [p for p in candidatos if p["precio"] <= filtros["presupuesto"]]
    if filtros.get("categoria"):
        candidatos = [p for p in candidatos if p["categoria"] == filtros["categoria"]]

    def afinidad(producto: dict) -> tuple:
        # El color pedido pesa más que cualquier otro término; a igualdad, gana
        # el más barato. Aquí se cambiaría por similitud de embeddings al escalar.
        con_color = filtros.get("color") and filtros["color"] in producto["texto"]
        return (1 if con_color else 0, -producto["precio"])

    return sorted(candidatos, key=afinidad, reverse=True)[:k]
