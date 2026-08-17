import { useEffect, useState } from "react";
import { getRole, hasRole, type Role } from "@/lib/auth";

/**
 * SSR-safe versions of getRole()/hasRole().
 *
 * This app is server-rendered (TanStack Start), but role/auth state
 * lives in localStorage, which doesn't exist during server rendering.
 * Calling hasRole()/getRole() directly during render produces DIFFERENT
 * output on the server (no localStorage -> defaults to "Viewer") vs the
 * client's first render (real role from localStorage) -- React detects
 * that mismatch, throws a hydration error, and discards + rebuilds the
 * whole tree, which can eat click events and break navigation right
 * after page load.
 *
 * Fix: stay at the safe "Viewer" default (least privilege, matching
 * what SSR renders) through the FIRST client render too, and only
 * switch to the real role in an effect after mount. Server output and
 * the client's first render now match exactly; the real role appears a
 * moment later without a mismatch. A brief flash of "locked" controls
 * before the real role loads is normal and expected.
 */
export function useRole(): Role {
  const [role, setRole] = useState<Role>("Viewer");

  useEffect(() => {
    setRole(getRole());
  }, []);

  return role;
}

export function useHasRole(minRole: Role): boolean {
  const [allowed, setAllowed] = useState(false); // matches SSR: least privilege

  useEffect(() => {
    setAllowed(hasRole(minRole));
  }, [minRole]);

  return allowed;
}
