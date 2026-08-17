import { useState } from "react";
import { useRouter } from "@tanstack/react-router";
import { Tag, Loader2, Pencil, Check, X } from "lucide-react";
import { toast } from "sonner";
import { setRootCauseCategory } from "@/lib/human-review-api";
import { useHasRole } from "@/hooks/use-role";
import { cn } from "@/lib/utils";

const ROOT_CAUSE_CATEGORIES = [
  "Port / logistics congestion",
  "Customs / documentation",
  "Supplier capacity issues",
  "Quality control",
  "Other",
];

interface Props {
  exceptionId: string;
  category?: string | null;
  source?: "auto" | "human" | null;
}

/**
 * Shows the auto-classified (or human-corrected) root cause category as
 * a tag, with an inline edit control for Procurement Manager+ to correct
 * it -- the "tagging" half of the Root Cause Analysis feature. Keyword
 * matching (see backend app/root_cause.py) deliberately won't catch
 * everything, so this exists to close that gap without needing a
 * database console.
 */
export function RootCauseCategoryTag({ exceptionId, category, source }: Props) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [selected, setSelected] = useState(category ?? ROOT_CAUSE_CATEGORIES[0]);
  const [saving, setSaving] = useState(false);
  const canEdit = useHasRole("Procurement Manager");

  async function handleSave() {
    setSaving(true);
    try {
      await setRootCauseCategory(exceptionId, selected);
      toast.success("Root cause category updated");
      setEditing(false);
      await router.invalidate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to update category");
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground"
        >
          {ROOT_CAUSE_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-60"
          title="Save"
        >
          {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
        </button>
        <button
          onClick={() => setEditing(false)}
          disabled={saving}
          className="inline-flex h-6 w-6 items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-accent"
          title="Cancel"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {category ? (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
            "border-border bg-muted text-foreground",
          )}
        >
          <Tag className="h-3 w-3" />
          {category}
          {source === "human" && (
            <span className="text-[10px] text-muted-foreground">(tagged by reviewer)</span>
          )}
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-border px-2.5 py-1 text-xs text-muted-foreground">
          <Tag className="h-3 w-3" />
          Uncategorized
        </span>
      )}
      {canEdit && (
        <button
          onClick={() => setEditing(true)}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <Pencil className="h-3 w-3" />
          {category ? "Correct" : "Tag it"}
        </button>
      )}
    </div>
  );
}
