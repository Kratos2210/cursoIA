"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useState,
  type ReactNode,
} from "react";
import { usePathname } from "next/navigation";

// Interactive quiz for the converted MDX (v2 look). The MDX emits:
//   <Quiz title="…"><Question><Prompt/><Option ok/><Option/><Feedback/></Question>…</Quiz>
// Each part renders itself and reads shared state via context — no children
// introspection, so it works across the Server→Client boundary and in SSR.
//
// Answers persist per page in localStorage under `curso_ia_quiz`, keyed by
// pathname → { [questionId]: { optId, ok } }. The ids come from useId(), which
// is deterministic for a given (static) tree, so the same question/option map to
// the same key on every reload.

const STORAGE_KEY = "curso_ia_quiz";
type Picked = { optId: string; ok: boolean };
type PageAnswers = Record<string, Picked>;

function readAll(): Record<string, PageAnswers> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}
function writePage(pathname: string, answers: PageAnswers) {
  try {
    const all = readAll();
    all[pathname] = answers;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
  } catch {
    /* ignore quota / private mode */
  }
}

const QuizCtx = createContext<{
  register: (qid: string) => void;
  choose: (qid: string, optId: string, ok: boolean) => void;
  answers: PageAnswers;
} | null>(null);

const QuestionCtx = createContext<{
  answered: boolean;
  pickedId: string | null;
  choose: (optId: string, ok: boolean) => void;
} | null>(null);

export function Quiz({ title, children }: { title?: string; children?: ReactNode }) {
  const pathname = usePathname();
  const [qids, setQids] = useState<Set<string>>(() => new Set());
  const [answers, setAnswers] = useState<PageAnswers>({});

  // Hydrate saved answers for this page after mount (render-neutral first, so
  // SSR and the first client render match).
  useEffect(() => {
    setAnswers(readAll()[pathname] ?? {});
  }, [pathname]);

  const register = useCallback((qid: string) => {
    setQids((s) => (s.has(qid) ? s : new Set(s).add(qid)));
  }, []);

  const choose = useCallback(
    (qid: string, optId: string, ok: boolean) => {
      setAnswers((prev) => {
        if (qid in prev) return prev; // first answer wins
        const next = { ...prev, [qid]: { optId, ok } };
        writePage(pathname, next); // write-through, no clobber of the empty init
        return next;
      });
    },
    [pathname]
  );

  const total = qids.size;
  const answeredCount = Object.keys(answers).length;
  const correct = Object.values(answers).filter((a) => a.ok).length;
  const allDone = total > 0 && answeredCount === total;

  return (
    <QuizCtx.Provider value={{ register, choose, answers }}>
      <div className="quiz">
        {title ? <div className="quiz-head">{title}</div> : null}
        <div className="quiz-sub">
          <span className="hint">Responde para ver si ya lo tienes</span>
          <span className="quiz-score-wrap" aria-live="polite">
            {allDone ? (
              <span className={`quiz-score${correct === total ? " perfect" : ""}`}>
                {correct} / {total}
              </span>
            ) : null}
          </span>
        </div>
        {children}
      </div>
    </QuizCtx.Provider>
  );
}

export function Question({ children }: { children?: ReactNode }) {
  const qid = useId();
  const quiz = useContext(QuizCtx);

  useEffect(() => {
    quiz?.register(qid);
  }, [quiz, qid]);

  const picked = quiz?.answers[qid] ?? null;
  const answered = picked !== null;

  const choose = useCallback(
    (optId: string, ok: boolean) => quiz?.choose(qid, optId, ok),
    [quiz, qid]
  );

  return (
    <div className="q">
      <QuestionCtx.Provider value={{ answered, pickedId: picked?.optId ?? null, choose }}>
        {children}
      </QuestionCtx.Provider>
    </div>
  );
}

export function Prompt({ children }: { children?: ReactNode }) {
  return <p className="enun">{children}</p>;
}

export function Option({ ok = false, children }: { ok?: boolean; children?: ReactNode }) {
  const optId = useId();
  const q = useContext(QuestionCtx);
  const answered = !!q?.answered;

  let cls = "opt";
  if (answered) {
    if (ok) cls += " correct";
    else if (q?.pickedId === optId) cls += " wrong";
    else cls += " dim";
  }

  return (
    <button
      type="button"
      className={cls}
      disabled={answered}
      onClick={() => q?.choose(optId, ok)}
    >
      {children}
    </button>
  );
}

export function Feedback({ children }: { children?: ReactNode }) {
  const q = useContext(QuestionCtx);
  if (!q?.answered) return null;
  return (
    <p className="fb" aria-live="polite">
      {children}
    </p>
  );
}
