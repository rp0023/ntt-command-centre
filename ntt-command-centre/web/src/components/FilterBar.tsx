/** Reusable selectors for the one server-side page slice. */
import { useEffect, useId, useRef, useState } from "react";
import type { DimKey, Measure, MetaPayload, PersonaKey } from "../api/types";

export type MetaDimension = MetaPayload["dimensions"][number];

export const FILTER_DIMS_BY_PERSONA: Record<PersonaKey, DimKey[]> = {
  ae: ["stage", "forecast", "lob", "portfolio", "account", "orderType"],
  manager: ["rep", "stage", "lob", "portfolio", "orderType", "quarter"],
  executive: ["lob", "portfolio", "industry", "country", "quarter", "orderType", "stage"],
};

const LONG_LIST = 25;

export function FilterSelect({
  dimension,
  value,
  onSet,
  idPrefix,
}: {
  dimension: MetaDimension;
  value: string | null | undefined;
  onSet: (dim: DimKey, value: string | null) => void;
  idPrefix: string;
}) {
  const generated = useId().replace(/:/g, "");
  const id = `${idPrefix}-${dimension.key}-${generated}`;
  const long = dimension.values.length > LONG_LIST;

  return (
    <span className={`filter-field${value ? " filter-field--on" : ""}`}>
      <label className="filter-field__label" htmlFor={id}>{dimension.label}</label>
      <select
        id={id}
        className="filter-field__select"
        value={value ?? ""}
        title={`${dimension.description} ${dimension.basisNote}`}
        onChange={(event) => onSet(dimension.key, event.target.value || null)}
      >
        <option value="">{long ? `All ${dimension.values.length}` : "All"}</option>
        {dimension.values.map((option) => (
          <option value={option} key={option}>{option}</option>
        ))}
      </select>
    </span>
  );
}

export function MeasureToggle({ measure, onMeasure }: {
  measure: Measure;
  onMeasure: (measure: Measure) => void;
}) {
  return (
    <span className="measure-control">
      <span className="measure-control__label">Show</span>
      <span className="seg" role="group" aria-label="Measure">
        {(["gp", "revenue"] as Measure[]).map((option) => (
          <button
            type="button"
            key={option}
            className={`segbtn${measure === option ? " on" : ""}`}
            aria-pressed={measure === option}
            onClick={() => onMeasure(option)}
          >
            {option === "gp" ? "Profit" : "Revenue"}
          </button>
        ))}
      </span>
    </span>
  );
}

export function MoreFilters({ dimensions, active, onSet, onClear }: {
  dimensions: MetaDimension[];
  active: Partial<Record<DimKey, string | null>>;
  onSet: (dim: DimKey, value: string | null) => void;
  onClear: () => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const activeCount = dimensions.filter((dimension) => active[dimension.key]).length;

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      triggerRef.current?.focus();
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (dimensions.length === 0) return null;

  return (
    <div className="more-filters" ref={rootRef}>
      <button
        type="button"
        className={`more-filters__trigger${activeCount ? " more-filters__trigger--on" : ""}`}
        ref={triggerRef}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        More filters{activeCount ? ` (${activeCount})` : ""}
      </button>
      {open ? (
        <section className="more-filters__popover" role="dialog" aria-label="More page filters">
          <div className="more-filters__head">
            <div>
              <strong>Filter this page</strong>
              <p>Selections update every summary, action, and chart.</p>
            </div>
            <button
              type="button"
              className="more-filters__close"
              aria-label="Close more filters"
              onClick={() => { setOpen(false); triggerRef.current?.focus(); }}
            >
              ×
            </button>
          </div>
          <div className="more-filters__fields">
            {dimensions.map((dimension) => (
              <FilterSelect
                key={dimension.key}
                dimension={dimension}
                value={active[dimension.key]}
                onSet={onSet}
                idPrefix="more-filter"
              />
            ))}
          </div>
          {Object.values(active).some(Boolean) ? (
            <button type="button" className="more-filters__clear" onClick={onClear}>
              Clear all filters
            </button>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
