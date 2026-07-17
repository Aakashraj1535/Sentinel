import { useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { getExceptions, getSuppliers, type ExceptionRecord, type Supplier } from "@/lib/mock-api";
import { cn } from "@/lib/utils";

type Result =
  | { kind: "exception"; id: string; title: string; subtitle: string }
  | { kind: "supplier"; id: string; title: string; subtitle: string };

export function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [exceptions, setExceptions] = useState<ExceptionRecord[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [active, setActive] = useState(0);
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getExceptions().then(setExceptions);
    getSuppliers().then(setSuppliers);
  }, []);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const results = useMemo<Result[]>(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const ex: Result[] = exceptions
      .filter(
        (e) =>
          e.id.toLowerCase().includes(q) ||
          e.supplier.toLowerCase().includes(q) ||
          e.type.toLowerCase().includes(q),
      )
      .slice(0, 6)
      .map((e) => ({
        kind: "exception",
        id: e.id,
        title: `${e.id} · ${e.type}`,
        subtitle: e.supplier,
      }));
    const sup: Result[] = suppliers
      .filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.id.toLowerCase().includes(q) ||
          s.region.toLowerCase().includes(q),
      )
      .slice(0, 4)
      .map((s) => ({
        kind: "supplier",
        id: s.id,
        title: s.name,
        subtitle: `${s.id} · ${s.region}`,
      }));
    return [...ex, ...sup];
  }, [query, exceptions, suppliers]);

  function go(r: Result) {
    setOpen(false);
    setQuery("");
    if (r.kind === "exception") {
      navigate({ to: "/exceptions/$exceptionId", params: { exceptionId: r.id } });
    } else {
      navigate({ to: "/suppliers" });
    }
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            setActive(0);
          }}
          onFocus={() => query && setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActive((a) => Math.min(a + 1, results.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => Math.max(a - 1, 0));
            } else if (e.key === "Enter" && results[active]) {
              e.preventDefault();
              go(results[active]);
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder="Search exceptions, suppliers…"
          className="w-full rounded-md border border-border bg-surface pl-8 pr-8 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring/40"
        />
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setOpen(false);
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {open && query && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-80 overflow-auto rounded-md border border-border bg-popover shadow-lg">
          {results.length === 0 ? (
            <div className="px-3 py-4 text-xs text-muted-foreground text-center">
              No matches
            </div>
          ) : (
            <ul className="py-1">
              {results.map((r, i) => (
                <li key={`${r.kind}-${r.id}`}>
                  <button
                    onMouseEnter={() => setActive(i)}
                    onClick={() => go(r)}
                    className={cn(
                      "flex w-full items-center gap-2 px-3 py-2 text-left text-sm",
                      i === active ? "bg-accent" : "hover:bg-accent/60",
                    )}
                  >
                    <span
                      className={cn(
                        "shrink-0 rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wide font-mono",
                        r.kind === "exception"
                          ? "bg-[color-mix(in_oklab,var(--info)_14%,transparent)] text-[color-mix(in_oklab,var(--info)_55%,black)]"
                          : "bg-muted text-muted-foreground",
                      )}
                    >
                      {r.kind === "exception" ? "EX" : "SUP"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium">{r.title}</div>
                      <div className="truncate text-xs text-muted-foreground">
                        {r.subtitle}
                      </div>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
