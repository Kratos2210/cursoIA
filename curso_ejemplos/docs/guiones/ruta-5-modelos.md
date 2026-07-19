# Guion · Ruta 5 — Modelos: mecánica, fine-tuning y multimodal (6–7 min)

**Se publica en:** c27 · **Demo:** softmax y top_p calculados a mano — y en el playground

## Gancho (0:00–0:30)

> Llevas meses poniendo `temperature=0.7` porque lo viste en un ejemplo. En
> esta ruta abres la caja: qué es un token de verdad, qué deforma la
> temperatura, por qué `top_p=0.5` puede ser un determinismo disfrazado — y
> cuándo fine-tunear en vez de hacer RAG. Todo con aritmética que puedes
> comprobar a mano, sin fe.

## Qué vas a poder hacer (0:30–1:15)

- Explicar (con números) temperatura, top_k, top_p y perplejidad — y dejar de ajustarlos a ciegas.
- Decidir fine-tuning vs RAG con criterio de negocio, y correr un LoRA real en Colab.
- Mandar imágenes y audio al modelo (bloques tipados) y armar el pipeline de voz en tiempo real.
- Leer la ficha técnica de un modelo y elegir proveedor con el embudo caro→barato (c18b).

## Demo (1:15–4:30) — offline, pura aritmética

```bash
cd curso_ejemplos
uv run python 27_fundamentos_llm.py
```

Puntos de guion:
- «Predice: ¿cuántos tokens cuesta "proyectos" si "proyecto" cuesta 5?» Correr.
  «Uno más. El plural cuesta un token. Por eso tu factura depende del IDIOMA.»
- Pantalla partida con el playground del c27: bajar temperatura a 0.1 → «mira
  el aviso: con estos logits, 0.1 YA es 0. "Casi determinista" es determinista.»
- Bajar top_p a 0.5 → el núcleo queda en un token. «Tu compañero cree que 0.5
  es más creativo. Ahora puedes demostrarle con la pantalla que es lo contrario.»

## Recorrido de la ruta (4:30–5:45)

- **c27** la mecánica (lo que viste) · **c27b** transformer, RLHF, MoE — la historia que explica el presente.
- **c28** alucinaciones: taxonomía y detector medible. **c18b** elegir modelo y proveedor con precios verificados.
- **c21/c21b** fine-tuning vs RAG + LoRA hands-on. **c22/c33** multimodal y voz en tiempo real.

## Cierre (5:45–6:15)

> Después de esta ruta, los parámetros dejan de ser supersticiones. Empieza por
> el c27 — y juega con el playground hasta que los números te cuadren.

**CTA:** `/concepto/27-fundamentos-del-llm`
