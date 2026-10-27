import { Suspense } from "react";
import Link from "next/link";

import { PageHeader } from "@/components/app/page-header";
import { buttonClasses } from "@/components/ui/button";
import { getContext } from "@/lib/session";

import { NewTenantButton } from "./new-tenant-button";
import { TenantsSection } from "./tenants-section";

export type TenantsSearchParams = Promise<{
  search?: string | string[];
  status?: string | string[];
  created?: string | string[];
}>;

export default function TenantsPage({
  searchParams,
}: {
  searchParams: TenantsSearchParams;
}) {
  return (
    <div className="mx-auto w-full max-w-[1000px]">
      <PageHeader
        title="Tenants"
        description="Customer organisations. Each Tenant has one Data Source."
        actions={<NewTenantButton />}
      />
      <Suspense fallback={<TenantsFallback />}>
        <TenantsAccess searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function TenantsAccess({
  searchParams,
}: {
  searchParams: TenantsSearchParams;
}) {
  const { context } = await getContext();

  if (context.identity.role !== "platform_admin") {
    return (
      <div className="mx-auto w-full max-w-[680px] py-16">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          You do not have access to this page
        </h1>
        <p className="mt-2 text-base text-muted-foreground">
          Tenants are managed by a Platform Admin.
        </p>
        <Link
          href="/conversations"
          className={buttonClasses({ variant: "secondary", className: "mt-5" })}
        >
          Back to Conversations
        </Link>
      </div>
    );
  }

  return (
    <TenantsSection
      searchParams={searchParams}
      currentTenantId={context.tenant?.id ?? null}
    />
  );
}

function TenantsFallback() {
  return (
    <div aria-hidden="true" className="space-y-4">
      <div className="h-11 w-full animate-pulse rounded-control bg-muted" />
      <div className="h-64 rounded-card border border-border bg-card" />
    </div>
  );
}