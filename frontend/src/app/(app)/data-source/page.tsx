import { Suspense } from "react";
import Link from "next/link";

import { PageHeader } from "@/components/app/page-header";
import { buttonClasses } from "@/components/ui/button";
import { serverFetch } from "@/lib/api.server";
import { getContext } from "@/lib/session";
import type { ConnectionFields, DataSource } from "@/lib/types";

import { DataSourceCard } from "./data-source-card";

export default function DataSourcePage() {
  return (
    <div className="mx-auto w-full max-w-[760px]">
      <PageHeader
        title="Data Source"
        description="Where this Tenant’s business data lives. Access is read-only."
      />
      <Suspense fallback={<DataSourceFallback />}>
        <DataSourceAccess />
      </Suspense>
    </div>
  );
}

async function DataSourceAccess() {
  const { context } = await getContext();

  if (context.identity.role === "user") {
    return (
      <div className="mx-auto w-full max-w-[680px] py-16">
        <h2 className="text-3xl font-semibold tracking-tight text-foreground">
          You do not have access to this page
        </h2>
        <p className="mt-2 text-base text-muted-foreground">
          The Data Source is managed by a Tenant Admin.
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

  if (context.identity.role === "platform_admin" && !context.tenant) {
    return (
      <p className="rounded-card border border-border bg-card px-6 py-7 text-center text-muted-foreground shadow-card">
        Choose a Tenant to connect its Data Source.
      </p>
    );
  }

  const [dataSource, connectionFields] = await Promise.all([
    serverFetch<DataSource | null>("/data-source"),
    serverFetch<ConnectionFields>("/data-source/fields"),
  ]);

  return (
    <DataSourceCard
      dataSource={dataSource}
      connectionFields={connectionFields.fields}
    />
  );
}

function DataSourceFallback() {
  return (
    <div aria-hidden="true">
      <div className="h-56 animate-pulse rounded-card border border-border bg-card" />
    </div>
  );
}