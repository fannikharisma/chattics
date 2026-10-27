import Link from "next/link";

import { EmptyState } from "@/components/app/empty-state";
import { StatusChip } from "@/components/app/status-chip";
import { buttonClasses } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { serverFetch } from "@/lib/api.server";
import type { Tenant } from "@/lib/types";

import { TenantsFilters } from "./tenants-filters";
import { TenantRowActions } from "./tenant-row-actions";
import type { TenantsSearchParams } from "./page";

const STATUSES = new Set(["all", "active", "disabled"]);
type StatusFilter = "all" | "active" | "disabled";

function first(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

function statusFilter(value: string): StatusFilter {
  return STATUSES.has(value) ? (value as StatusFilter) : "all";
}

async function loadCreated(id: string): Promise<Tenant | null> {
  if (!id) return null;
  try {
    return await serverFetch<Tenant>(`/tenants/${encodeURIComponent(id)}`);
  } catch {
    return null;
  }
}

export async function TenantsSection({
  searchParams,
  currentTenantId,
}: {
  searchParams: TenantsSearchParams;
  currentTenantId: string | null;
}) {
  const params = await searchParams;
  const search = first(params.search).trim();
  const status = statusFilter(first(params.status));
  const createdId = first(params.created);

  const query = new URLSearchParams();
  query.set("status", status);
  if (search) query.set("search", search);

  const [tenants, created] = await Promise.all([
    serverFetch<Tenant[]>(`/tenants?${query.toString()}`),
    loadCreated(createdId),
  ]);

  const filtered = Boolean(search) || status !== "all";

  return (
    <>
      {created && (
        <div
          role="status"
          className="mb-4 rounded-card border border-border bg-secondary px-4 py-3 text-sm text-secondary-foreground"
        >
          Created <strong>{created.name}</strong>. Its Tenant Admin signs in by
          choosing {created.name} and entering{" "}
          <strong>{created.admin_email}</strong>.{" "}
          <Link href="/tenants" className="underline underline-offset-2">
            Dismiss
          </Link>
        </div>
      )}

      <TenantsFilters initialSearch={search} />

      <div className="mt-3 overflow-hidden rounded-card border border-border bg-card">
        {tenants.length === 0 ? (
          <EmptyState
            action={
              filtered ? (
                <Link
                  href="/tenants"
                  className={buttonClasses({ variant: "secondary", size: "sm" })}
                >
                  Clear search
                </Link>
              ) : undefined
            }
          >
            {filtered
              ? "No Tenant matches."
              : "No Tenants yet. Use New Tenant to add the first one."}
          </EmptyState>
        ) : (
          <Table aria-label="Tenants">
            <TableHeader>
              <tr>
                <TableHead>Tenant</TableHead>
                <TableHead>Data Source</TableHead>
                <TableHead className="text-right">Users</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </tr>
            </TableHeader>
            <TableBody>
              {tenants.map((tenant) => (
                <TableRow key={tenant.id}>
                  <TableCell className="font-medium">{tenant.name}</TableCell>
                  <TableCell>
                    {tenant.data_source_state === "connected"
                      ? "Connected"
                      : "Not connected"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {tenant.user_count}
                  </TableCell>
                  <TableCell>
                    <StatusChip
                      tone={tenant.status === "active" ? "success" : "danger"}
                    >
                      {tenant.status === "active" ? "Active" : "Disabled"}
                    </StatusChip>
                  </TableCell>
                  <TableCell>
                    <TenantRowActions
                      tenant={tenant}
                      currentTenantId={currentTenantId}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </>
  );
}