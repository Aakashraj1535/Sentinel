import { Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Activity, Bell, BookOpen, Bot, ClipboardList, LayoutDashboard, Truck, Search, ChevronDown, LogOut, UserCog } from "lucide-react";
import type { ReactNode } from "react";
import { GlobalSearch } from "./GlobalSearch";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { getDisplayName, getRole, getInitials, logout } from "@/lib/auth";

const nav = [
  {
    section: "Overview",
    items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard, exact: true }],
  },
  {
    section: "Operations",
    items: [
      { to: "/audit", label: "Audit Trail", icon: ClipboardList, exact: false },
      { to: "/suppliers", label: "Suppliers", icon: Truck, exact: false },
      { to: "/activity-log", label: "Agent Activity", icon: Bot, exact: false },
    ],
  },
  {
    section: "Resources",
    items: [
      { to: "/knowledge-base", label: "Knowledge Base", icon: BookOpen, exact: false },
      { to: "/notifications", label: "Notifications", icon: Bell, exact: false },
    ],
  },
] as const;

export function AppShell({ children }: { children?: ReactNode }) {
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate({ to: "/login" });
  }

  function handleSwitchAccount() {
    // "Switch account" = sign out of the current role and land back on
    // /login so a different demo account can be chosen. There's no
    // multi-account session to switch between under the hood -- this is
    // still a single-session demo, just a clearer label/flow than
    // silently logging out.
    logout();
    navigate({ to: "/login" });
  }

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      {/* ---------------- SIDEBAR ---------------- */}
      <aside className="hidden md:flex md:w-60 md:flex-col bg-sidebar text-sidebar-foreground shrink-0">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
            <Activity className="h-4 w-4" />
            <span className="absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-sidebar" />
          </div>
          <div className="leading-tight">
            <div className="text-[13px] font-semibold tracking-tight">Sentinel</div>
            <div className="text-[10px] uppercase tracking-wider text-sidebar-foreground/50">
              Supply Chain Ops
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-2 space-y-5 overflow-y-auto">
          {nav.map((group) => (
            <div key={group.section}>
              <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">
                {group.section}
              </div>
              <div className="space-y-0.5">
                {group.items.map((n) => {
                  const Icon = n.icon;
                  return (
                    <Link
                      key={n.to}
                      to={n.to}
                      activeOptions={{ exact: n.exact }}
                      activeProps={{
                        className: "bg-sidebar-accent text-sidebar-accent-foreground border-l-2 border-sidebar-primary",
                      }}
                      inactiveProps={{
                        className: "text-sidebar-foreground/65 hover:bg-sidebar-accent/50 border-l-2 border-transparent",
                      }}
                      className="flex items-center gap-2.5 rounded-r-md pl-2.5 pr-3 py-1.5 text-[13px] font-medium transition-colors"
                    >
                      <Icon className="h-[15px] w-[15px]" />
                      {n.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="px-4 py-3 border-t border-sidebar-border">
          <div className="flex items-center gap-1.5 px-2 text-[10px] text-sidebar-foreground/45">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            System online
          </div>
        </div>
      </aside>

      {/* ---------------- MAIN ---------------- */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* Mobile top bar */}
        <header className="md:hidden flex items-center gap-2 border-b border-border bg-surface px-4 py-3 no-print">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Activity className="h-3.5 w-3.5" />
          </div>
          <span className="text-sm font-semibold">Sentinel</span>
        </header>

        {/* Desktop top header bar */}
        <div className="hidden md:flex items-center justify-between border-b border-border bg-surface px-6 py-3 no-print">
          <div className="flex-1 max-w-md">
            <GlobalSearch />
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              aria-label="Search"
            >
              <Search className="h-4 w-4" />
            </button>
            <Link
              to="/notifications"
              className="relative flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              aria-label="Notifications"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-danger" />
            </Link>
            <div className="ml-2 pl-3 border-l border-border flex items-center gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className="flex items-center gap-1.5 rounded-full transition-opacity hover:opacity-80"
                    aria-label="Account menu"
                  >
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary text-[11px] font-semibold">
                      {getInitials()}
                    </div>
                    <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" side="bottom" className="w-56">
                  <DropdownMenuLabel>
                    <div className="text-sm font-medium">{getDisplayName()}</div>
                    <div className="text-xs font-normal text-muted-foreground">
                      Signed in as {getRole()}
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleSwitchAccount}>
                    <UserCog className="h-4 w-4" />
                    Switch account
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleLogout} className="text-danger focus:text-danger">
                    <LogOut className="h-4 w-4" />
                    Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>

        <div className="md:hidden border-b border-border bg-surface px-4 py-2.5 no-print">
          <GlobalSearch />
        </div>

        <div className="flex-1 mx-auto w-full max-w-[1400px] px-6 py-6">
          {children ?? <Outlet />}
        </div>
      </main>
    </div>
  );
}
