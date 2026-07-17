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

// Interactive quiz for the converted MDX (v2 look). The MDX emits:
//   <Quiz title="…"><Question><Prompt/><Option ok/><Option/><Feedback/></Question>…</Quiz>
// Each part renders itself and reads shared state via context — no children
// introspection, so it works across the Server→Client boundary and in SSR.

const QuizCtx = createContext<{
  register: (qid: string) => void;
  report: (qid: string, ok: boolean) => void;
} | null>(null);

const QuestionCtx = createContext<{
  answered: boolean;
  pickedId: string | null;
  choose: (optId: string, ok: boolean) => void;
} | null>(null);

export function Quiz({ title, children }: { title?: string; children?: ReactNode }) {
  const [qids, setQids] = useState<Set<string>>(() => new Set());
  const [results, setResults] = useState<Record<string, boolean>>({});

  const register = useCallback((qid: string) => {
    setQids((s) => (s.has(qid) ? s : new Set(s).add(qid)));
  }, []);
  const report = useCallback((qid: string, ok: boolean) => {
    setResults((r) => (qid in r ? r : { ...r, [qid]: ok }));
  }, []);

  const total = qids.size;
  const answered = Object.keys(results).length;
  const correct = Object.values(results).filter(Boolean).length;
  const allDone = total > 0 && answered === total;

  return (
    <QuizCtx.Provider value={{ register, report }}>
      <div className="quiz">
        {title ? <div className="quiz-head">{title}</div> : null}
        <div className="quiz-sub">
          <span className="hint">Responde para ver si ya lo tienes</span>
          {allDone ? (
            <span className={`quiz-score${correct === total ? " perfect" : ""}`}>
              {correct} / {total}
            </span>
          ) : null}
        </div>
        {children}
      </div>
    </QuizCtx.Provider>
  );
}

export function Question({ children }: { children?: ReactNode }) {
  const qid = useId();
  const quiz = useContext(QuizCtx);
  const [answered, setAnswered] = useState(false);
  const [pickedId, setPickedId] = useState<string | null>(null);

  useEffect(() => {
    quiz?.register(qid);
  }, [quiz, qid]);

  const choose = useCallback(
    (optId: string, ok: boolean) => {
      setAnswered((prev) => {
        if (prev) return prev;
        setPickedId(optId);
        quiz?.report(qid, ok);
        return true;
      });
    },
    [quiz, qid]
  );

  return (
    <div className="q">
      <QuestionCtx.Provider value={{ answered, pickedId, choose }}>{children}</QuestionCtx.Provider>
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
  return <p className="fb">{children}</p>;
}
