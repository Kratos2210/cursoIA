# Guiones de video — uno por ruta

Ocho videos de 5–10 minutos, uno abriendo cada ruta del curso. No repiten el
contenido escrito: **venden la ruta** (qué vas a poder hacer al terminarla) y
muestran UNA demo corta corriendo de verdad. El detalle vive en la web; el
video es el gancho y la prueba de que funciona.

| # | Guion | Estado | Se publica en |
|---|-------|--------|---------------|
| 1 | [ruta-1-fundamentos.md](ruta-1-fundamentos.md) | 📝 por grabar | c00 `00-preparar-el-terreno` |
| 2 | [ruta-2-prompts-lcel.md](ruta-2-prompts-lcel.md) | 📝 por grabar | c02 `02-prompts-lcel` |
| 3 | [ruta-3-agentes.md](ruta-3-agentes.md) | 📝 por grabar | c07 `07-herramientas` |
| 4 | [ruta-4-rag.md](ruta-4-rag.md) | 📝 por grabar | c11 `11-rag-profesional` |
| 5 | [ruta-5-modelos.md](ruta-5-modelos.md) | 📝 por grabar | c27 `27-fundamentos-del-llm` |
| 6 | [ruta-6-produccion.md](ruta-6-produccion.md) | 📝 por grabar | c17 `17-repo-productivo` |
| 7 | [ruta-7-proyectos.md](ruta-7-proyectos.md) | 📝 por grabar | c35 `35-discovery-de-procesos` |
| 8 | [ruta-8-cierre.md](ruta-8-cierre.md) | 📝 por grabar | c26 `26-mapa-del-ecosistema` |

## Cómo publicar un video (2 pasos)

1. Grabar y subir a YouTube (público o no listado).
2. Poner la URL en el campo `videoUrl` del módulo correspondiente en
   `web/content/modules.manifest.json`. Nada más: la página del concepto
   muestra sola el reproductor (lite-embed de `youtube-nocookie`, sin cookies
   hasta que el alumno pulsa play), y `verificar_curso.py` valida que la URL
   sea de YouTube.

## Formato de cada guion

- **Gancho (0:00–0:30)**: el problema en una frase, sin saludo largo.
- **Qué vas a poder hacer** (3 bullets, resultados — no temas).
- **Demo** (2–4 min): comandos exactos del repo, en pantalla.
- **Recorrido de la ruta** (1 min): qué módulo aporta qué.
- **Cierre + CTA** (20 s): al primer módulo de la ruta.

Tono: hablarle a UNA persona, en tú. Cero jerga sin explicar en el video 1;
progresivamente técnico después. Los comandos se muestran, no se dictan.
