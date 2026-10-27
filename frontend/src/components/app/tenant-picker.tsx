"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApiError, apiFetch } from "@/lib/api";
import type { Context, Tenant } from "@/lib/types";

const LOAD_MESSAGE = "Tenants could not be loaded. Please try again.";

type TenantPickerProps = {
  open: boolean;
  /** A Platform Admin with no Tenant cannot dismiss this without choosing. */
  blocking: boolean;
  explanation?: string | null;
  onOpenChange: (open: boolean) => void;
  onSelected: (tenantName: string) => void;
};

export function TenantPicker({
  open,
  blocking,
  explanation,
  onOpenChange,
  onSelected,
}: TenantPickerProps) {
  const router = useRouter();
  const [tenants, setTenants] = useState<Tenant[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [choosing, setChoosing] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const loading = tenants === null && error === null;

  useEffect(() => {
    if (!open || tenants !== null) return;
    let cancelled = false;
    void (async () => {
      try {
        const active = await apiFetch<Tenant[]>("/tenants?status=active");
        if (!cancelled) setTenants(active);
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : LOAD_MESSAGE);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, tenants, reloadToken]);

  function retry() {
    setError(null);
    setTenants(null);
    setReloadToken((current) => current + 1);
  }

  async function choose(tenant: Tenant) {
    setChoosing(tenant.id);
    setError(null);
    try {
      await apiFetch<Context>("/context/tenant", {
        method: "PUT",
        body: JSON.stringify({ tenant_id: tenant.id }),
      });
      onSelected(tenant.name);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "That Tenant could not be selected. Please try again.",
      );
      setTenants(null);
    } finally {
      setChoosing(null);
    }
  }

  function goToTenants() {
    onOpenChange(false);
    router.push("/tenants");
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && blocking) return;
        onOpenChange(next);
      }}
    >
      <DialogContent
        showClose={!blocking}
        onEscapeKeyDown={(event) => {
          if (blocking) event.preventDefault();
        }}
        onPointerDownOutside={(event) => {
          if (blocking) event.preventDefault();
        }}
        onInteractOutside={(event) => {
          if (blocking) event.preventDefault();
        }}
      >
        <DialogHeader>
          <DialogTitle>Which Tenant do you want to work in?</DialogTitle>
          <DialogDescription>
            Everything you see next belongs to this Tenant. You can change it
            later.
          </DialogDescription>
        </DialogHeader>

        {explanation && (
          <p
            role="status"
            className="mt-4 rounded-control bg-warning-bg px-3 py-2 text-sm text-warning"
          >
            {explanation}
          </p>
        )}

        <div
          className="mt-4 max-h-[55vh] space-y-2 overflow-y-auto"
          aria-busy={loading}
        >
          {loading && (
            <p className="py-3 text-sm text-muted-foreground">
              Loading Tenants…
            </p>
          )}

          {error && (
            <div
              role="alert"
              className="rounded-control border border-destructive/40 bg-danger-bg px-3 py-2 text-sm text-destructive"
            >
              <p>{error}</p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-2"
                onClick={retry}
              >
                Try again
              </Button>
            </div>
          )}

          {!loading && tenants?.length === 0 && (
            <div className="py-3">
              <p className="text-sm text-muted-foreground">
                No active Tenant yet. Create one on the Tenants screen first.
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-3"
                onClick={goToTenants}
              >
                Go to Tenants
              </Button>
            </div>
          )}

          {tenants?.map((tenant) => (
            <button
              key={tenant.id}
              type="button"
              disabled={choosing !== null}
              onClick={() => void choose(tenant)}
              className="block min-h-[52px] w-full rounded-card border border-border bg-card px-3.5 py-3 text-left transition-colors duration-150 hover:border-primary disabled:opacity-60"
            >
              <span className="block text-sm font-medium text-foreground">
                {tenant.name}
              </span>
              <span className="block text-meta text-muted-foreground">
                {tenant.admin_email ?? "No Tenant Admin yet"}
              </span>
              <span className="sr-only">Work in this Tenant</span>
            </button>
          ))}
        </div>

        {!blocking && (
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
