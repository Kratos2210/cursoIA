Plan: convertir el curso en material de estudio robusto y end-to-end
El material actual es didácticamente sólido pero le falta "cierre": no hay nada que garantice que los ejemplos siguen corriendo, ni ejercicios que consoliden, ni archivos ejecutables para varios temas que hoy solo son teoría en el HTML. Este plan ataca las 4 direcciones que pediste, manteniendo el estilo didáctico existente (FINALIDAD/LÓGICA/Requisitos, comentarios línea por línea).

Fase 1 — Infraestructura de calidad (lo primero, porque habilita todo lo demás)
1.1 Entorno reproducible

Crear pyproject.toml en la raíz del proyecto con dependencias pinneadas (mismas que requirements.txt) + grupo dev con pytest.
Añadir uv.lock (generado, no editado a mano).
Crear .gitignore (Python + venv + .env + __pycache__) y eliminar __pycache__/ commiteado.
Mantener requirements.txt como compatibilidad (generado/actualizado, con comment de que el canon es pyproject.toml).
1.2 Tests offline (pytest) — estructura tests/:

tests/conftest.py: fixtures compartidas (cargar datos_rag.txt, paths, mock de modelo opcional).
tests/test_offline.py: tests por ejemplo de las partes no-LLM:
07: calculadora_descuentos(3500,18)==2870, metadatos .name/.description/.args.
05: instanciar/validar los 3 modelos Pydantic (Persona, Extraccion, Etiqueta).
06: RunnableLambda(upper) + RunnablePassthrough + RunnableParallel sin API.
11: función unir(docs) y troceado por "\n\n" (extraerlas a función pura si hace falta).
12: BM25, coseno, fusión RRF, re-ranking contra datos_rag.txt (detallado, bien offline).
13b: grafo HITL completo sin API (incluye la rama de reanudar con Command(resume=...)).
14: cliente MCP descubriendo tools (offline, sin LLM).
tests/test_imports.py: smoke test que importa todos los módulos (catcha roturas de versiones sin gastar cuota).
Para los ejemplos 02/03/04/08/09/10/13 (acoplados al LLM): refactor mínimo extrayendo la lógica pura a funciones importables (ej: manejar_error_429(exc) en un util.py) para poder testearlas, sin cambiar la salida del ejemplo.
1.3 CI (GitHub Actions)

.github/workflows/ci.yml: corre pytest tests/ en Python 3.11 y 3.12 en cada push/PR. NO llama a la API (solo tests offline). Opcionalmente corre uv pip install para validar que las dependencias resuelven.
Fase 2 — Más contenido didáctico
2.1 Ejercicios propuestos — carpeta ejercicios/ con un README.md índice y, por tema, un ejercicio_NN.md con: enunciado, pistas (progresivas), criterio de aceptación, y referencia al ejemplo resuelto. Temas:

ejercicio_04_memoria.md: añadir 3er turno + "resumir historial largo" (ventana).
ejercicio_05_estructurada.md: añadir un 4º molde Pydantic para un caso nuevo.
ejercicio_07_tools.md: crear 2 tools nuevas y combinarlas en 08.
ejercicio_11_rag.md: cambiar k, añadir un documento y verificar anti-alucinación.
ejercicio_12_rerank.md: modificar la pregunta y predecir el ranking antes de ejecutar.
ejercicio_13_hitl.md: añadir un nodo de "escalado" cuando el humano rechaza.
ejercicio_proyecto.md: extender el proyecto final (ver 2.3).
Se incluye una carpeta ejercicios/soluciones/ con las resoluciones, claramente separadas para que el estudiante decida verlas.
2.2 Dos ejemplos nuevos (cubren brechas reales del HTML):

15_supervisor_multiagente.py: patrón supervisor con LangGraph (un orquestador decide entre 2 sub-agentes). Domínio: gobierno de datos (un agente "consultor de normativa" + un agente "evaluador de calidad"). Mantiene el hilo conductor. 100% offline posible simulando, o con API como los demás.
17_servidor_agente.py: interfaz real que consume el agente — FastAPI mínimo (POST /chat) + opcional Gradio. Cierra el gap "el estudiante nunca ve el agente conectado a algo que usaría un usuario".
2.3 Proyecto final modular (fase 4 detallada abajo)

Fase 3 — Cierre de temas teóricos del HTML (archivos ejecutables para lo que hoy es solo teoría)
16b_observabilidad_langsmith.py: versión real del tema 16 con langsmith tracing (cuando hay LANGSMITH_API_KEY) y conteo de tokens/coste real (response_metadata de Gemini). Degradación graceful: si no hay key, cae al modo offline actual.
docs/ con tres archivos de referencia ejecutables/operativos:
docs/README_runbook.md: el README del curso reescrito como runbook de operación (cómo levantar, variables de entorno, qué hacer ante 429, cómo depurar un grafo, rollback).
docs/adr/0001-vector-store.md y docs/adr/0002-re-ranker.md: los ADRs que el HTML muestra como ejemplo, materializados como archivos reales (plantilla ADR + 2 ejemplos).
Ampliar el README.md principal: índice actualizado a 17 temas, tabla "concepto → archivo → ejercicio → test", y sección "cómo se verifica que esto funciona" (apuntando a la CI).
Fase 4 — Proyecto final modular
Refactor de proyecto_final/app.py (hoy 158 líneas monolíticas) a la estructura que el propio HTML prescribe (state.py / graph_builder.py / rag.py / persistence.py / audit.py / config.py / main.py), + tests. Esto convierte el proyecto final en el ejemplo viviente del tema "de un archivo gigante a un agente modular".

proyecto_final/config.py: carga de .env, rutas, constantes, modelo LLM.
proyecto_final/rag.py: lectura de normativa, troceado, vector store, retriever, contexto().
proyecto_final/audit.py: modelo HallizgoCalidad (Pydantic), registrar_auditoria(), lectura del log.
proyecto_final/tools.py: buscar_normativa, evaluar_regla_calidad (usan rag.py + audit.py).
proyecto_final/state.py y graph_builder.py: el agente LangGraph con checkpointer (igual que hoy, pero modular y testeable).
proyecto_final/persistence.py: wrapper sobre MemorySaver con comentario de cómo cambiar a SqliteSaver/PostgresSaver.
proyecto_final/main.py: punto de entrada (la demo de 2 turnos).
proyecto_final/tests/: tests offline de rag.trocear, audit.HallizgoCalidad, registrar_auditoria, y un smoke del grafo con LLM mockeado.
proyecto_final/app.py: se mantiene como shim de compatibilidad (importa de main) para no romper el README existente.
Orden de ejecución sugerido (cuando se implemente)
Fase 1 (infraestructura + tests) — sin esto, lo demás no se puede verificar.
Fase 4 (proyecto modular) — el ejemplo más valioso del curso, y sus tests piden los de Fase 1.
Fase 3 (cierre teórico).
Fase 2 (ejercicios + 2 ejemplos nuevos).
Notas de alcance
No se cambia el proveedor (sigue Gemini) ni los modelos de los ejemplos existentes salvo el refactor mínimo de Fase 1.2 para extraer funciones testeables.
Todo lo nuevo respeta el estilo de comentarios del curso y funciona en español.
Las dependencias nuevas mínimas: pytest, langsmith, fastapi (para 17). Se añaden a pyproject.toml (FastAPI en opcional/extras para no inflar).
Lo que NO incluye este plan
No despliego nada real (no Docker/K8s reales): el HTML ya los cubre teóricamente; aquí solo dejamos el terreno preparado (Dockerfile opcional si lo pides).
No reescribo el HTML del curso (solo referencio sus secciones al añadir archivos).
