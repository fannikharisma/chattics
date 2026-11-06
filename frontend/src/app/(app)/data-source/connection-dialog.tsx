"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ConnectionChecklist } from "@/components/app/connection-checklist";
import { Button, buttonClasses } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, apiFetch } from "@/lib/api";
import type {
  ConnectionField,
  ConnectionTest,
  DataSource,
} from "@/lib/types";

type Values = Record<string, string>;

function defaults(
  connectionFields: ConnectionField[],
  dataSource: DataSource | null,
): Values {
  const stored: Values = {
    ...(dataSource?.fields ?? {}),
    ...(dataSource
      ? { engine: dataSource.engine, method: dataSource.method }
      : {}),
  };

  return Object.fromEntries(
    connectionFields.map((field) => {
      const saved = stored[field.key];
      if (saved) return [field.key, saved] as const;

      const firstEnabled = field.options?.find((option) => !option.disabled);
      return [field.key, firstEnabled?.value ?? ""] as const;
    }),
  );
}

export function ConnectionDialog({
  open,
  autoTest,
  onOpenChange,
  connectionFields,
  dataSource,
  onSaved,
}: {
  open: boolean;
  autoTest: boolean;
  onOpenChange: (open: boolean) => void;
  connectionFields: ConnectionField[];
  dataSource: DataSource | null;
  onSaved: () => void;
}) {
  const router = useRouter();
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ConnectionTest | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const wasOpen = useRef(false);

  const schema = useMemo(
    () =>
      z.object(
        Object.fromEntries(
          connectionFields.map((field) => [
            field.key,
            field.required
              ? z.string().trim().min(1, `Fill in ${field.label}.`)
              : z.string().trim(),
          ]),
        ),
      ),
    [connectionFields],
  );

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: defaults(connectionFields, dataSource),
  });

  const canSave = result !== null && result.error === null && !testing;

  const onTest = useCallback(async (values: Values) => {
    setTesting(true);
    setFormError(null);
    setResult(null);

    try {
      const response = await apiFetch<ConnectionTest>("/data-source/test", {
        method: "POST",
        body: JSON.stringify(values),
      });
      setResult(response);
    } catch (error) {
      setFormError(
        error instanceof ApiError
          ? error.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setTesting(false);
    }
  }, []);

  async function onSave(values: Values) {
    if (!canSave) return;

    setFormError(null);
    try {
      await apiFetch<DataSource>("/data-source", {
        method: "PUT",
        body: JSON.stringify(values),
      });
      onSaved();
      onOpenChange(false);
      router.refresh();
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "test_required") setResult(null);
        for (const [field, message] of Object.entries(error.fields ?? {})) {
          if (field in values) form.setError(field, { message });
        }
        setFormError(error.message);
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    }
  }

  // Each open starts from the saved values. "Test again" also runs the test.
  useEffect(() => {
    if (open && !wasOpen.current) {
      form.reset(defaults(connectionFields, dataSource));
      setResult(null);
      setFormError(null);
      if (autoTest) void form.handleSubmit(onTest)();
    }
    wasOpen.current = open;
  }, [open, autoTest, connectionFields, dataSource, form, onTest]);

  // Editing any field invalidates the last passing test.
  useEffect(() => {
    const subscription = form.watch((_values, info) => {
      if (info.type === undefined) return; // programmatic reset
      setResult(null);
      setFormError(null);
    });
    return () => subscription.unsubscribe();
  }, [form]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Connect Data Source</DialogTitle>
          <DialogDescription>
            Test the connection before saving. Access is read-only.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSave)} noValidate>
          {connectionFields.map((field) => {
            const error = form.formState.errors[field.key]?.message;
            const message = typeof error === "string" ? error : undefined;
            const invalid = Boolean(message);

            return (
              <FormField
                key={field.key}
                id={field.key}
                label={field.label}
                help={field.help_text ?? undefined}
                error={message}
              >
                {field.kind === "select" ? (
                  <NativeSelect
                    id={field.key}
                    disabled={testing}
                    aria-invalid={invalid}
                    aria-describedby={invalid ? `${field.key}-error` : undefined}
                    {...form.register(field.key)}
                  >
                    {(field.options ?? []).map((option) => (
                      <option
                        key={option.value}
                        value={option.value}
                        disabled={option.disabled}
                      >
                        {option.label}
                      </option>
                    ))}
                  </NativeSelect>
                ) : (
                  <Input
                    id={field.key}
                    autoComplete="off"
                    spellCheck={false}
                    disabled={testing}
                    placeholder={field.placeholder ?? undefined}
                    aria-invalid={invalid}
                    aria-describedby={invalid ? `${field.key}-error` : undefined}
                    {...form.register(field.key)}
                  />
                )}
              </FormField>
            );
          })}

          {formError && (
            <p role="alert" className="mt-3 text-sm text-destructive">
              {formError}
            </p>
          )}

          {testing && (
            <p role="status" className="mt-4 text-sm text-muted-foreground">
              Testing connection…
            </p>
          )}

          {!testing && result && (
            <div className="mt-4">
              <ConnectionChecklist
                items={result.checklist}
                error={result.error}
              />

              {result.error === null && (
                <div className="mt-3">
                  <p className="text-sm text-foreground">
                    Connection works. Found {result.tables.length}{" "}
                    {result.tables.length === 1 ? "table" : "tables"}.
                  </p>

                  {result.tables.length > 0 && (
                    <div className="mt-2 overflow-hidden rounded-card border border-border">
                      <Table aria-label="Tables found">
                        <TableHeader>
                          <tr>
                            <TableHead>Table</TableHead>
                            <TableHead className="text-right">Columns</TableHead>
                          </tr>
                        </TableHeader>
                        <TableBody>
                          {result.tables.map((table) => (
                            <TableRow key={table.name}>
                              <TableCell>{table.name}</TableCell>
                              <TableCell className="text-right tabular-nums">
                                {table.column_count}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}

                  <p className="mt-2 text-meta text-muted-foreground">
                    Next, describe these tables in the Semantic Layer.
                  </p>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <DialogClose className={buttonClasses({ variant: "secondary" })}>
              Cancel
            </DialogClose>
            <Button
              variant="secondary"
              onClick={form.handleSubmit(onTest)}
              disabled={testing}
            >
              {testing ? "Testing…" : "Test connection"}
            </Button>
            <Button
              type="submit"
              disabled={!canSave || form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? "Saving…" : "Save Data Source"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}