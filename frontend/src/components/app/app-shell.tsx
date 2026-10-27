"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { TenantPicker } from "@/components/app/tenant-picker";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import {
  TENANT_SELECTED_EVENT,
  type TenantSelectedDetail,
} from "@/lib/context-events";
import { menuHref, roleLabel } from "@/lib/menus";
import { cn } from "@/lib/utils";
import type { ContextIdentity, ContextTenant } from "@/lib/types";

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
  identity: ContextIdentity;
  tenant: ContextTenant | null;
  menus: string[];
  tenantDisabled: boolean;
  children: ReactNode;
};

export function AppShell({
  identity,
  tenant,
  menus,
  tenantDisabled,
  children,
}: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState(false);

  const isPlatformAdmin = identity.role === "platform_admin";
  // Tenants is the one Menu a Platform Admin can use without a selection.
  const onTenants = pathname === "/tenants" || pathname.startsWith("/tenants/");
  const needsTenant = isPlatformAdmin && tenant === null && !onTenants;

  const [pickerOpen, setPickerOpen] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(
    tenantDisabled
      ? "The Tenant you were working in is disabled. Choose another one."
      : null,
  );
  const [notice, setNotice] = useState<string | null>(null);
  const pickerVisible = pickerOpen || needsTenant;

  useEffect(() => {
    const stored = window.localStorage.getItem(SIDEBAR_KEY);
    // The stored preference only exists in the browser; reading it during
    // hydration would disagree with the server-rendered closed sidebar.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setOpen(
      stored === "shown"
        ? true
        : stored === "hidden"
          ? false
          : window.matchMedia("(min-width: 1024px)").matches,
    );
  }, []);

  const handleSelected = useCallback(
    (name: string) => {
      setPickerOpen(false);
      setExplanation(null);
      setNotice(
        `Data Source, Model, Semantic Layer, Users and Query Log now use ${name}.`,
      );
      router.refresh();
    },
    [router],
  );

  useEffect(() => {
    function onTenantSelected(event: Event) {
      const detail = (event as CustomEvent<TenantSelectedDetail>).detail;
      if (detail?.name) handleSelected(detail.name);
    }
    window.addEventListener(TENANT_SELECTED_EVENT, onTenantSelected);
    return () =>
      window.removeEventListener(TENANT_SELECTED_EVENT, onTenantSelected);
  }, [handleSelected]);

  function toggleSidebar() {
    setOpen((current) => {
      const next = !current;
      window.localStorage.setItem(SIDEBAR_KEY, next ? "shown" : "hidden");
      return next;
    });
  }

  function openPicker() {
    setExplanation(null);
    setPickerOpen(true);
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

        {isPlatformAdmin && (
          <div className="px-3 pb-2 pt-3">
            {tenant ? (
              <>
                <p className="px-2 text-sm text-muted-foreground">
                  Working in{" "}
                  <span className="font-medium text-foreground">
                    {tenant.name}
                  </span>{" "}
                  <button
                    type="button"
                    onClick={openPicker}
                    className="text-primary underline underline-offset-2"
                  >
                    Change
                  </button>
                </p>
                <p className="mt-1 px-2 text-meta text-muted-foreground">
                  Data Source, Model, Semantic Layer, Users and Query Log use
                  this Tenant.
                </p>
              </>
            ) : (
              <p className="px-2 text-sm text-muted-foreground">
                No Tenant selected.{" "}
                <button
                  type="button"
                  onClick={openPicker}
                  className="text-primary underline underline-offset-2"
                >
                  Choose
                </button>
              </p>
            )}
          </div>
        )}

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
              {initials(identity.full_name)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground">
                {identity.full_name}
              </p>
              <p className="truncate text-meta text-muted-foreground">
                {roleLabel(identity.role)}
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
          {notice && (
            <p
              role="status"
              className="mx-auto mb-4 w-full max-w-[1000px] rounded-control bg-secondary px-3 py-2 text-sm text-secondary-foreground"
            >
              {notice}
            </p>
          )}
          {children}
        </main>
      </div>

      <TenantPicker
        open={pickerVisible}
        blocking={needsTenant}
        explanation={explanation}
        onOpenChange={setPickerOpen}
        onSelected={handleSelected}
      />
    </div>
  );
}
