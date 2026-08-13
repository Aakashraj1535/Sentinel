import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { login } from "@/lib/auth";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const ok = login(username, password);
    if (ok) {
      navigate({ to: "/" });
    } else {
      setError("Invalid username or password.");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-input bg-card p-8 shadow-sm"
      >
        <h1 className="text-xl font-semibold text-foreground">
          Supply Chain Sentinel
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Sign in to continue
        </p>

        <div className="mt-6 space-y-4">
          <div>
            <label className="text-sm font-medium text-foreground">
              Username
            </label>
            <input
              type="text"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-primary"
              placeholder="admin"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-primary"
              placeholder="********"
            />
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <button
            type="submit"
            className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
          >
            Sign in
          </button>
        </div>

        <p className="mt-4 text-xs text-muted-foreground">
          Demo accounts (password for all: <code>sentinel2026</code>):
          <br />
          <code>viewer</code> — Viewer (read-only)
          <br />
          <code>manager</code> — Procurement Manager (can approve/reject, add
          notes, trigger pipeline runs)
          <br />
          <code>admin</code> — Admin (also manages suppliers and the
          knowledge base)
        </p>
      </form>
    </div>
  );
}
