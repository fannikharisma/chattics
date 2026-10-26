"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { menuHref, roleLabel } from "@/lib/menus";
import { cn } from "@/lib/utils";
import type { User } from "@/lib/types";

const SIDEBAR_KEY = "chattics.sidebar";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

type AppShellProps = {
  user: User;
  menus: string[];
  children: ReactNode;
};

export function AppShell({ user, menus, children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem(SIDEBAR_KEY);
    setOpen(
      stored === "shown"
        ? true
        : stored === "hidden"
          ? false
          : window.matchMedia("(min-width: 1024px)").matches,
    );
  }, []);

  function toggleSidebar() {
    setOpen((current) => {
      const next = !current;
      window.localStorage.setItem(SIDEBAR_KEY, next ? "shown" : "hidden");
      return next;
    });
  }

  async function signOut() {
    setSigningOut(true);
    setSignOutError(false);
    try {
      await apiFetch<void>("/auth/sign-out", { method: "POST" });
      router.replace("/sign-in");
      router.refresh();
    } catch {
      setSignOutError(true);
    } finally {
      setSigningOut(false);
    }
  }

  const items = menus
    .map((label) => ({ label, href: menuHref(label) }))
    .filter((item): item is { label: string; href: string } => item.href !== null);

  return (
    <div className="flex min-h-dvh flex-col bg-background lg:flex-row">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-control focus:bg-card focus:px-4 focus:py-2 focus:text-sm focus:shadow-card"
      >
        Skip to content
      </a>

      <aside
        id="app-sidebar"
        className={cn(
          "flex w-full shrink-0 flex-col border-b border-border bg-tint-strong lg:sticky lg:top-0 lg:h-dvh lg:w-66 lg:overflow-y-auto lg:border-b-0 lg:border-r",
          open ? "flex" : "hidden",
        )}
      >
        <div className="flex items-center justify-between px-4 pt-4">
          <span className="text-xl font-semibold text-primary">Chattics</span>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Hide menu"
            onClick={toggleSidebar}
          >
            <PanelLeftClose aria-hidden="true" className="h-5 w-5" />
          </Button>
        </div>

        <nav aria-label="Menu" className="flex-1 px-3 py-4">
          <p className="px-2 pb-2 text-xs font-medium text-muted-foreground">
            Menu
          </p>
          <ul className="space-y-1">
            {items.map((item) => {
              const active =
                pathname === item.href ||
                pathname.startsWith(`${item.href}/`);
              return (
                <li key={item.label}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex h-11 items-center rounded-control px-3 text-sm transition-colors duration-150",
                      active
                        ? "bg-accent font-medium text-accent-foreground"
                        : "text-foreground hover:bg-muted",
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="border-t border-border p-3">
          <div className="flex items-center gap-3">
            <span
              aria-hidden="true"
              className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-secondary text-sm font-semibold text-secondary-foreground"
            >
              {initials(user.full_name)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground">
                {user.full_name}
              </p>
              <p className="truncate text-meta text-muted-foreground">
                {roleLabel(user.role)}
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Sign out"
              title="Sign out"
              onClick={signOut}
              disabled={signingOut}
            >
              <LogOut aria-hidden="true" className="h-5 w-5" />
            </Button>
          </div>
          {signOutError && (
            <p role="alert" className="mt-2 text-meta text-destructive">
              Could not sign out. Please try again.
            </p>
          )}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center border-b border-border bg-card px-3">
          <Button
            variant="ghost"
            size="icon"
            aria-label={open ? "Hide menu" : "Show menu"}
            aria-expanded={open}
            aria-controls="app-sidebar"
            onClick={toggleSidebar}
          >
            {open ? (
              <PanelLeftClose aria-hidden="true" className="h-5 w-5" />
            ) : (
              <PanelLeftOpen aria-hidden="true" className="h-5 w-5" />
            )}
          </Button>
        </header>

        <main
          id="main"
          className="min-w-0 flex-1 px-4 py-6 md:px-6 lg:px-8"
        >
          {children}
        </main>
      </div>
    </div>
  );
}