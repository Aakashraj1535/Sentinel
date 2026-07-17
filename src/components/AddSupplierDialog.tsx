import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { addSupplier } from "@/lib/suppliers-api";
import type { Supplier } from "@/lib/mock-api";

const REGIONS = ["APAC", "EMEA", "AMER", "LATAM", "MEA"] as const;

export function AddSupplierDialog({
  open,
  onOpenChange,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onAdded: (s: Supplier) => void;
}) {
  const [name, setName] = useState("");
  const [region, setRegion] = useState<string>("APAC");
  const [onTimeRate, setOnTimeRate] = useState<number>(100);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) {
      setName("");
      setRegion("APAC");
      setOnTimeRate(100);
      setSubmitting(false);
    }
  }, [open]);

  const handleSubmit = async () => {
    if (!name.trim()) {
      toast.error("Supplier name is required.");
      return;
    }
    if (onTimeRate < 0 || onTimeRate > 100 || Number.isNaN(onTimeRate)) {
      toast.error("On-time rate must be between 0 and 100.");
      return;
    }
    setSubmitting(true);
    try {
      const supplier = await addSupplier({
        name: name.trim(),
        region,
        onTimeRate,
      });
      toast.success("Supplier added");
      onAdded(supplier);
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add supplier");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add supplier</DialogTitle>
          <DialogDescription>
            Register a new supplier in the network. Incidents and risk will be
            tracked automatically from this point forward.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="supplier-name">Name</Label>
            <Input
              id="supplier-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Meridian Logistics Co."
            />
          </div>

          <div className="grid gap-2">
            <Label>Region</Label>
            <Select value={region} onValueChange={setRegion}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {REGIONS.map((r) => (
                  <SelectItem key={r} value={r}>
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="on-time-rate">Starting on-time rate (%)</Label>
            <Input
              id="on-time-rate"
              type="number"
              min={0}
              max={100}
              step={0.1}
              value={onTimeRate}
              onChange={(e) => setOnTimeRate(parseFloat(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">
              Between 0 and 100. Defaults to 100 for new suppliers.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={submitting || !name.trim()}>
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Adding…
              </>
            ) : (
              <>
                <Plus className="h-4 w-4" />
                Add supplier
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
