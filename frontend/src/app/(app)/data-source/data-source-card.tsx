"use client";

import { useState } from "react";
import Link from "next/link";

import { EmptyState } from "@/components/app/empty-state";
import { StatusChip } from "@/components/app/status-chip";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { ConnectionField, DataSource } from "@/lib/types";

import { ConnectionDialog } from "./connection-dialog";

export function DataSourceCard({
  dataSource,
  connectionFields,
}: {
  dataSource: DataSource | null;
  connectionFields: ConnectionField[];
}) {
  const [open, setOpen] = useState(false);
  const [autoTest, setAutoTest] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  function openDialog(test: boolean) {
    setAutoTest(test);
    setJustSaved(false);
    setOpen(true);
  }

  function changeOpen(next: boolean) {
    setOpen(next);
    if (!next) setAutoTest(false);
  }

  const connected = dataSource?.status === "connected";

  return (
    <>
      {justSaved && (
        <p
          role="status"
          className="mb-4 rounded-card border border-border bg-secondary px-4 py-3 text-sm text-secondary-foreground"
        >
          Data Source saved. Next step: Model settings.
        </p>
      )}

      <Card>
        {dataSource === null ? (
          <EmptyState
            title="No Data Source yet"
            action={
              <Button onClick={() => openDialog(false)}>
                Connect Data Source
              </Button>
            }
          >
            Connect your database so Users can ask Questions about it.
          </EmptyState>
        ) : (
          <div className="p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-foreground">
                  {displayLabel(connectionFields, "engine", dataSource.engine)}
                </h2>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  {connected
                    ? "Tested and saved."
                    : "Tested but not saved yet."}
                </p>
              </div>
              <StatusChip tone={connected ? "success" : "warning"}>
                {connected ? "Connected" : "Not connected"}
              </StatusChip>
            </div>

            <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-[160px_1fr]">
              <dt className="text-muted-foreground">Method</dt>
              <dd className="text-foreground">
                {displayLabel(connectionFields, "method", dataSource.method)}
              </dd>

              <dt className="text-muted-foreground">Project</dt>
              <dd className="break-words text-foreground">
                {dataSource.fields.project_id ?? "—"}
              </dd>

              <dt className="text-muted-foreground">Dataset</dt>
              <dd className="break-words text-foreground">
                {dataSource.fields.dataset ?? "—"}
              </dd>

              <dt className="text-muted-foreground">Tables found</dt>
              <dd className="tabular-nums text-foreground">
                {dataSource.tables.length}
              </dd>
            </dl>

            <div className="mt-5 flex flex-wrap gap-3">
              <Button variant="secondary" onClick={() => openDialog(false)}>
                {connected ? "Edit connection" : "Finish connection"}
              </Button>
              <Button variant="secondary" onClick={() => openDialog(true)}>
                Test again
              </Button>
            </div>

            {connected ? (
              <p className="mt-4 text-meta text-muted-foreground">
                Next step:{" "}
                <Link
                  href="/model-settings"
                  className="text-primary underline underline-offset-2"
                >
                  Model settings
                </Link>
              </p>
            ) : (
              <p className="mt-4 text-meta text-muted-foreground">
                Finish the setup to start using this Data Source.
              </p>
            )}
          </div>
        )}
      </Card>

      <ConnectionDialog
        open={open}
        autoTest={autoTest}
        onOpenChange={changeOpen}
        connectionFields={connectionFields}
        dataSource={dataSource}
        onSaved={() => setJustSaved(true)}
      />
    </>
  );
}

function displayLabel(
  fields: ConnectionField[],
  key: string,
  value: string,
): string {
  const field = fields.find((candidate) => candidate.key === key);
  const option = field?.options?.find((candidate) => candidate.value === value);
  return option?.label ?? value;
}