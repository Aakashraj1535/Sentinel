import type { Supplier } from "./mock-api";
import { roleHeaders } from "./backend-api";

const BASE_URL = "http://localhost:8080";

export interface AddSupplierInput {
  name: string;
  region: string;
  onTimeRate: number;
}

export async function addSupplier(input: AddSupplierInput): Promise<Supplier> {
  const body = new FormData();
  body.append("name", input.name);
  body.append("region", input.region);
  body.append("on_time_rate", String(input.onTimeRate));

  const res = await fetch(`${BASE_URL}/api/suppliers`, {
    method: "POST",
    headers: roleHeaders(),
    body,
  });
  if (res.status === 403) {
    throw new Error("You don't have permission to add suppliers (Admin only).");
  }
  if (!res.ok) {
    throw new Error(`Failed to add supplier (${res.status})`);
  }
  return (await res.json()) as Supplier;
}
