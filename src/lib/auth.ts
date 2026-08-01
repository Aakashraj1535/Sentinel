/**
 * Simple DEMO authentication for Supply Chain Sentinel.
 * -----------------------------------------------------
 * This is intentionally basic: one hardcoded username/password, session
 * flag stored in localStorage. It exists to demonstrate that the system
 * is access-controlled, not to be production-grade security.
 *
 * A real deployment would replace this with proper authentication
 * (e.g. OAuth/SSO via the company's identity provider) and role-based
 * access control (different views for warehouse staff, procurement
 * managers, and executives) -- this is a stated limitation, not an
 * oversight.
 */

const AUTH_KEY = "scs_auth_token";
const DEMO_USERNAME = "admin";
const DEMO_PASSWORD = "sentinel2026";

export function login(username: string, password: string): boolean {
  const ok = username === DEMO_USERNAME && password === DEMO_PASSWORD;
  if (ok && typeof window !== "undefined") {
    window.localStorage.setItem(AUTH_KEY, "true");
  }
  return ok;
}

export function logout(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(AUTH_KEY);
  }
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(AUTH_KEY) === "true";
}
