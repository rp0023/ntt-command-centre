import type { ReactNode } from "react";
import { outlineQuestion } from "../lib/questionOutline";

/** "You asked" as points: the subject, the facts sent with it, and what was
 *  asked for. A plain question renders `fallback`, i.e. as typed. */
export function AskedOutline({ question, fallback }: { question: string; fallback: ReactNode }) {
  const outline = outlineQuestion(question);
  if (!outline) return <>{fallback}</>;
  return <div className="ask-turn__insight-question">
    <strong>{outline.title}</strong>
    <dl>
      {outline.details.length ? <div><dt>Context</dt><dd><ul>{outline.details.map((item, index) => <li key={index}>{item}</li>)}</ul></dd></div> : null}
      {outline.asks.length ? <div><dt>Asked to cover</dt><dd><ul>{outline.asks.map((item, index) => <li key={index}>{item}</li>)}</ul></dd></div> : null}
    </dl>
  </div>;
}
