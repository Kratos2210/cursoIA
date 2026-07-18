"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { LEVELS, type Item } from "@/lib/roadmap";

// Placement test. The questions run in roadmap order and each one belongs to a
// ruta; the recommendation is the FIRST ruta the learner cannot answer. Anything
// before it they already know, so they get to skip it — that is the whole point
// of the page: an experienced dev should not have to read "instala Python" to
// find out the course has something for them.

const STORAGE_KEY = "curso_ia_diagnostico";

type Q = { levelKey: string; prompt: string; hint: string };

const QUESTIONS: Q[] = [
  {
    levelKey: "Fundamentos",
    prompt: "¿Puedes crear un entorno de Python aislado, guardar una API key fuera del código y llamar a un modelo desde un script?",
    hint: "Entorno, variables de entorno y la primera llamada.",
  },
  {
    levelKey: "Fundamentos",
    prompt: "¿Sabes qué hace de verdad `temperature=0` y en qué se diferencia un SystemMessage de un HumanMessage?",
    hint: "Determinismo y los roles del mensaje.",
  },
  {
    levelKey: "Prompts y composición",
    prompt: "¿Puedes explicar qué hace `prompt | llm | parser` y por qué el orden importa?",
    hint: "LCEL: componer pasos como una línea de ensamblaje.",
  },
  {
    levelKey: "Prompts y composición",
    prompt: "¿Sabes forzar que el modelo devuelva un objeto validado (Pydantic) en vez de texto libre, y cuándo NO conviene?",
    hint: "Salida estructurada para que la consuma otro software.",
  },
  {
    levelKey: "Herramientas y Agentes",
    prompt: "¿Puedes darle una herramienta al modelo y explicar por qué su docstring forma parte del prompt?",
    hint: "Tools, y el bucle que decide cuándo llamarlas.",
  },
  {
    levelKey: "Herramientas y Agentes",
    prompt: "¿Sabes qué te da LangGraph que no te da un agente prebuilt, y cuándo vale la pena el cambio?",
    hint: "Estado explícito, ciclos y control del flujo.",
  },
  {
    levelKey: "RAG",
    prompt: "¿Puedes explicar por qué cambiar de modelo de embeddings con un índice ya construido lo invalida entero?",
    hint: "Indexar, recuperar y el bug silencioso de los espacios vectoriales.",
  },
  {
    levelKey: "RAG",
    prompt: "¿Sabes qué hace un re-ranker y por qué no puede rescatar un documento que la recuperación no trajo?",
    hint: "Recuperar ancho y barato, refinar caro sobre pocos.",
  },
  {
    levelKey: "Producción y LLMOps",
    prompt: "¿Puedes medir el costo por petición, trazar qué pasó dentro de una cadena y evaluar la calidad con un dataset?",
    hint: "Observabilidad, costo y evaluación automatizada.",
  },
  {
    levelKey: "Cierre",
    prompt: "¿Puedes explicar por dentro qué es un token, un logit y cómo softmax con temperatura elige la siguiente palabra?",
    hint: "La mecánica del modelo, no su API.",
  },
];

function firstModuleOf(levelKey: string): Item | undefined {
  return LEVELS.find((l) => l.key === levelKey)?.items[0];
}

export function Diagnostico() {
  const [answers, setAnswers] = useState<Record<number, boolean>>({});
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    try {
      setSaved(localStorage.getItem(STORAGE_KEY));
    } catch {
      /* private mode */
    }
  }, []);

  const answer = useCallback((i: number, known: boolean) => {
    setAnswers((prev) => ({ ...prev, [i]: known }));
  }, []);

  const reset = useCallback(() => {
    setAnswers({});
    setSaved(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* private mode */
    }
  }, []);

  const answeredAll = Object.keys(answers).length === QUESTIONS.length;

  // First gap wins: everything before it is already known.
  const firstGap = QUESTIONS.findIndex((_, i) => answers[i] === false);
  const gapLevel = answeredAll ? (firstGap === -1 ? null : QUESTIONS[firstGap].levelKey) : null;
  const target = gapLevel ? firstModuleOf(gapLevel) : null;
  const level = gapLevel ? LEVELS.find((l) => l.key === gapLevel) : null;

  useEffect(() => {
    if (!answeredAll) return;
    try {
      localStorage.setItem(STORAGE_KEY, gapLevel ?? "completo");
    } catch {
      /* private mode */
    }
  }, [answeredAll, gapLevel]);

  return (
    <div className="view">
      <h1>¿Por dónde empiezo?</h1>
      <p className="lede">
        Diez preguntas, ningún truco: marca con honestidad lo que ya sabes hacer. No se
        califica nada — solo sirve para decirte en qué ruta entrar y qué puedes saltarte.
      </p>

      {saved && !answeredAll ? (
        <div className="box def">
          <div className="box-lab">◈ Ya lo hiciste antes</div>
          <p>
            Tu último resultado te dejaba en{" "}
            <strong>{saved === "completo" ? "el cierre AI Engineer" : saved}</strong>. Puedes
            repetirlo si has avanzado desde entonces.
          </p>
        </div>
      ) : null}

      <div className="quiz">
        {QUESTIONS.map((q, i) => (
          <div className="q" key={i}>
            <p className="enun">
              {i + 1} · {q.prompt}
            </p>
            <p className="dg-hint">{q.hint}</p>
            <div className="dg-actions">
              <button
                type="button"
                className={`opt${answers[i] === true ? " correct" : ""}`}
                onClick={() => answer(i, true)}
              >
                Sí, lo sé hacer
              </button>
              <button
                type="button"
                className={`opt${answers[i] === false ? " wrong" : ""}`}
                onClick={() => answer(i, false)}
              >
                No, o no del todo
              </button>
            </div>
          </div>
        ))}
      </div>

      {answeredAll ? (
        <div className="box practice" aria-live="polite">
          <div className="box-lab">▸ Tu punto de entrada</div>
          {target && level ? (
            <>
              <p>
                Empieza en <strong>{level.name}</strong>. Las rutas anteriores las das por
                sabidas, así que puedes hojearlas y usarlas solo como consulta.
              </p>
              <p>
                <Link href={target.href}>
                  Ir a {target.num} · {target.title} →
                </Link>
              </p>
            </>
          ) : (
            <>
              <p>
                Respondiste que sí a todo: el temario base no te va a enseñar mucho nuevo.
                Ve directo a los proyectos y al cierre — ahí es donde se integra todo y donde
                aparecen los problemas que no salen en los tutoriales.
              </p>
              <p>
                <Link href="/recurso/examen">Prueba el examen final →</Link> o{" "}
                <Link href="/recurso/entrevista">el banco de entrevista →</Link>
              </p>
            </>
          )}
          <p>
            <button type="button" className="quiz-retry" onClick={reset}>
              ↺ Volver a empezar
            </button>
          </p>
        </div>
      ) : (
        <p className="dg-progress">
          {Object.keys(answers).length} de {QUESTIONS.length} respondidas
        </p>
      )}
    </div>
  );
}
