/**
 * Simple DEMO authentication + role-based access control for Supply Chain
 * Sentinel.
 * -----------------------------------------------------------------------
 * Three fixed demo accounts, one per role, session flag + role stored in
 * localStorage. Still intentionally basic — no real session/token, so a
 * determined caller could set headers directly against the API. The role
 * is ALSO enforced server-side (see backend/app/auth.py) precisely
 * because hiding a button here is not real access control on its own;
 * this file controls what the UI *shows*, the backend controls what
 * actually *happens*.
 *
 * A real deployment would replace this with proper authentication
 * (e.g. OAuth/SSO via the company's identity provider) issuing a signed
 * session the backend verifies, rather than a client-supplied role
 * header — that gap is a stated limitation, not an oversight.
 */

export type Role = "Viewer" | "Procurement Manager" | "Admin";

interface DemoAccount {
  username: string;
  password: string;
  role: Role;
  displayName: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  { username: "viewer", password: "sentinel2026", role: "Viewer", displayName: "Priya (Viewer)" },
  { username: "manager", password: "sentinel2026", role: "Procurement Manager", displayName: "Arjun (Procurement Manager)" },
  { username: "admin", password: "sentinel2026", role: "Admin", displayName: "Admin" },
];

const AUTH_KEY = "scs_auth_token";
const ROLE_KEY = "scs_auth_role";
const NAME_KEY = "scs_auth_name";

export function login(username: string, password: string): boolean {
  const account = DEMO_ACCOUNTS.find(
    (a) => a.username === username && a.password === password,
  );
  if (account && typeof window !== "undefined") {
    window.localStorage.setItem(AUTH_KEY, "true");
    window.localStorage.setItem(ROLE_KEY, account.role);
    window.localStorage.setItem(NAME_KEY, account.displayName);
  }
  return !!account;
}

export function logout(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(AUTH_KEY);
    window.localStorage.removeItem(ROLE_KEY);
    window.localStorage.removeItem(NAME_KEY);
  }
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(AUTH_KEY) === "true";
}

export function getRole(): Role {
  if (typeof window === "undefined") return "Viewer";
  const stored = window.localStorage.getItem(ROLE_KEY);
  return (stored as Role) ?? "Viewer";
}

export function getDisplayName(): string {
  if (typeof window === "undefined") return "Demo User";
  return window.localStorage.getItem(NAME_KEY) ?? "Demo User";
}

const ROLE_INITIALS: Record<string, string> = {
  Viewer: "VW",
  "Procurement Manager": "PM",
  Admin: "AD",
};

export function getInitials(): string {
  return ROLE_INITIALS[getRole()] ?? "US";
}

const ROLE_LEVELS: Record<Role, number> = {
  Viewer: 0,
  "Procurement Manager": 1,
  Admin: 2,
};

/** Returns true if the signed-in user's role meets or exceeds `minRole`. */
export function hasRole(minRole: Role): boolean {
  return ROLE_LEVELS[getRole()] >= ROLE_LEVELS[minRole];
}
