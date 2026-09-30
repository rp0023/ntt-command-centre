/**
 * Breaks a long, generated "Ask" question into a title, the facts it carries
 * and the things it asks for, so "You asked" reads as points rather than one
 * run-on sentence. A plain typed question returns null and shows as written.
 */
export interface QuestionOutline {
  title: string;
  details: string[];
  asks: string[];
}

const VERBS = "recommend|identify|show|validate|clarify|compare|explain|highlight|list|suggest|summari[sz]e|prioriti[sz]e|describe|assess|confirm|flag";
const ASK_START = new RegExp(`^(?:${VERBS})\\b`, "i");
const ASK_JOIN = new RegExp(`,\\s+(?:and\\s+)?(?=(?:${VERBS})\\b)|\\s+and\\s+(?=(?:${VERBS})\\b)`, "i");
const TITLE_JOIN = new RegExp(`,?\\s+and\\s+(?=(?:${VERBS}|which|where|why|how|what)\\b)`, "i");
const ABBREVIATION_END = /\b(?:Inc|Co|Ltd|Corp|Mr|Ms|Dr|St|vs|e\.g|i\.e)\.$/;

const tidy = (text: string) => {
  const t = text.trim().replace(/^and\s+/i, "").replace(/^(?:a|an)\s+/i, "")
    .replace(/^is owned by\b/i, "Owned by").replace(ABBREVIATION_END.test(text.trim()) ? /[;,]$/ : /[.;,]$/, "").trim();
  return t.charAt(0).toUpperCase() + t.slice(1);
};

function sentences(text: string): string[] {
  const out: string[] = [];
  let buffer = "";
  for (const piece of text.trim().split(/(?<=\.)\s+(?=[A-Z$0-9])/)) {
    buffer = buffer ? `${buffer} ${piece}` : piece;
    if (!ABBREVIATION_END.test(buffer)) { out.push(buffer); buffer = ""; }
  }
  if (buffer) out.push(buffer);
  return out;
}

/** Splits "a, b (c, d), and e" on the commas outside brackets. */
function listItems(text: string): string[] {
  const items: string[] = [];
  let depth = 0, start = 0;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === "(") depth++;
    else if (ch === ")") depth = Math.max(0, depth - 1);
    // A comma between digits ("$40,000") is part of the number, not a separator.
    else if (ch === "," && depth === 0 && !(/\d/.test(text[i - 1] ?? "") && /\d/.test(text[i + 1] ?? ""))) { items.push(text.slice(start, i)); start = i + 1; }
  }
  items.push(text.slice(start));
  // A trailing "and why" reads as part of the point before it.
  return items.map(tidy).filter(Boolean).reduce<string[]>((acc, item) => {
    if (/^why$/i.test(item) && acc.length) acc[acc.length - 1] += ", and why";
    else acc.push(item);
    return acc;
  }, []);
}

/** Index of the first ": " outside brackets, or -1. */
function topLevelColon(text: string): number {
  let depth = 0;
  for (let i = 0; i < text.length - 1; i++) {
    if (text[i] === "(") depth++;
    else if (text[i] === ")") depth = Math.max(0, depth - 1);
    else if (depth === 0 && text[i] === ":" && text[i + 1] === " ") return i;
  }
  return -1;
}

const askItems = (text: string) => text.split(ASK_JOIN).map(tidy).filter(Boolean);

export function outlineQuestion(question: string): QuestionOutline | null {
  const [first, ...rest] = sentences(question);
  if (!first) return null;
  const details: string[] = [];
  const asks: string[] = [];

  let title = first;
  const colon = topLevelColon(first);
  if (colon > 0) {
    title = first.slice(0, colon);
    for (const item of listItems(first.slice(colon + 2))) {
      (/^(?:which|where|why|how|what)\b/i.test(item) ? asks : details).push(item);
    }
  } else {
    const [head, ...tail] = first.split(TITLE_JOIN);
    title = head;
    if (tail.length) asks.push(...askItems(tail.join(" and ")));
  }

  for (const sentence of rest) {
    if (ASK_START.test(sentence)) asks.push(...askItems(sentence));
    else if (/^It (?:has|is)\s/i.test(sentence)) details.push(...listItems(sentence.replace(/^It (?:has|is)\s+/i, "")));
    else details.push(tidy(sentence));
  }

  if (!details.length && !asks.length) return null;
  return { title: tidy(title), details, asks };
}
