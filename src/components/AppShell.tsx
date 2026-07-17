import { Link, Outlet } from "@tanstack/react-router";
import { Activity, Bell, BookOpen, Bot, ClipboardList, LayoutDashboard, Truck } from "lucide-react";
import type { ReactNode } from "react";
import { GlobalSearch } from "./GlobalSearch";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { to: "/audit", label: "Audit Trail", icon: ClipboardList, exact: false },
  { to: "/suppliers", label: "Suppliers", icon: Truck, exact: false },
  { to: "/knowledge-base", label: "Knowledge Base", icon: BookOpen, exact: false },
  { to: "/activity-log", label: "Agent Activity", icon: Bot, exact: false },
  { to: "/notifications", label: "Notifications", icon: Bell, exact: false },
] as const;


export function AppShell({ children }: { children?: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="hidden md:flex md:w-64 md:flex-col bg-sidebar text-sidebar-foreground">
        <div className="flex items-center gap-2 px-6 py-5 border-b border-sidebar-border">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
            <Activity className="h-4 w-4" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight">Sentinel</div>
            <div className="text-[11px] text-sidebar-foreground/60">
              Exception Management
            </div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map((n) => {
            const Icon = n.icon;
            return (
              <Link
                key={n.to}
                to={n.to}
                activeOptions={{ exact: n.exact }}
                activeProps={{
                  className:
                    "bg-sidebar-accent text-sidebar-accent-foreground",
                }}
                inactiveProps={{
                  className: "text-sidebar-foreground/75 hover:bg-sidebar-accent/60",
                }}
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors"
              >
                <Icon className="h-4 w-4" />
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="px-6 py-4 border-t border-sidebar-border text-[11px] text-sidebar-foreground/60">
          v1.0 · Ops Console
        </div>
      </aside>
      <main className="flex-1 min-w-0">
        <header className="md:hidden flex items-center gap-2 border-b border-border bg-surface px-4 py-3 no-print">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Activity className="h-3.5 w-3.5" />
          </div>
          <span className="text-sm font-semibold">Sentinel</span>
        </header>
        <div className="hidden md:flex items-center justify-end border-b border-border bg-surface/60 px-6 py-2.5 no-print">
          <GlobalSearch />
        </div>
        <div className="md:hidden border-b border-border bg-surface/60 px-4 py-2.5 no-print">
          <GlobalSearch />
        </div>
        <div className="mx-auto max-w-[1400px] px-6 py-8">
          {children ?? <Outlet />}
        </div>
      </main>
    </div>
  );
}
