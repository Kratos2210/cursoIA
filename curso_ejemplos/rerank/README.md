# rerank/ — el re-ranker de verdad (cross-encoder) al lado del didáctico

El m12 implementa el re-ranking a mano —cobertura de palabras + bono de frase—
para que la mecánica se vea sin instalar nada (ADR-0002). Su fallo confesado: si
ninguna palabra de la pregunta aparece en el chunk, todos puntúan 0.0 y el orden
es arbitrario. `rerank_real.py` pone el re-ranker **real** al lado del didáctico,
sobre el MISMO corpus y la MISMA pregunta:

```
recuperar (rápido, tonto)  ->  re-rankear (lento, listo)
                               didáctico:  ¿comparten palabras?
                               REAL:       ¿este texto RESPONDE la pregunta?
```

Un cross-encoder lee pregunta y chunk JUNTOS: entiende sinónimos
("devolución" ~ "reembolso") donde el didáctico ve 0.0. Corre sobre fastembed
(ONNX, ~80 MB, sin PyTorch — que no tiene wheels para macOS Intel), no sobre
`HuggingFaceCrossEncoder`. Mismo concepto, otra caja.

## Cómo se corre

```bash
uv run --extra emb python rerank/rerank_real.py
```

Sin cuota de API: solo descarga el modelo (~80 MB) la primera vez. Reutiliza el
corpus y el re-ranker didáctico del m12 importándolos por ruta (el archivo
empieza por dígito).

## Por qué está fuera del gate offline

Decidido en [ADR-0008](../docs/adr/0008-re-ranker-real-companion.md): la
descarga del modelo lo saca de la CI. La mecánica testeada vive en
`12_rag_hibrido_rerank.py` (companion del [ADR-0002](../docs/adr/0002-re-ranker.md)).
