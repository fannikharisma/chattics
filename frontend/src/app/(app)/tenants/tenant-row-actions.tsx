"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { StatusChip } from "@/components/app/status-chip";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetBody,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ApiError, apiFetch } from "@/lib/api";
import { monthYear } from "@/lib/format";
import type { Tenant } from "@/lib/types";
import { cn } from "@/lib/utils";

const EMAIL_MESSAGE =
  "Enter the Tenant Admin's email, like name@company.com.";

const schema = z.object({
  name: z.string().trim().min(1, "Enter a Tenant name."),
  admin_email: z
    .string()
    .trim()
    .min(1, EMAIL_MESSAGE)
    .regex(/^[^@\s]+@[^@\s]+$/, EMAIL_MESSAGE),
  status: z.enum(["active", "disabled"]),
});

type Values = z.infer<typeof schema>;

export function TenantRowActions({ tenant }: { tenant: Tenant }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState<Values | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: tenant.name,
      admin_email: tenant.admin_email ?? "",
      status: tenant.status,
    },
  });

  function openDetails() {
    form.reset({
      name: tenant.name,
      admin_email: tenant.admin_email ?? "",
      status: tenant.status,
    });
    setEditing(false);
    setNotice(null);
    setFormError(null);
    setOpen(true);
  }

  function startEdit() {
    form.reset({
      name: tenant.name,
      admin_email: tenant.admin_email ?? "",
      status: tenant.status,
    });
    setEditing(true);
    setNotice(null);
    setFormError(null);
  }

  async function save(values: Values): Promise<boolean> {
    setSaving(true);
    setFormError(null);
    try {
      await apiFetch<Tenant>(`/tenants/${tenant.id}`, {
        method: "PATCH",
        body: JSON.stringify(values),
      });
      router.refresh();
      return true;
    } catch (error) {
      if (error instanceof ApiError) {
        let focus: keyof Values | null = null;
        for (const [field, message] of Object.entries(error.fields ?? {})) {
          if (field === "name" || field === "admin_email") {
            form.setError(field, { message });
            focus ??= field;
          }
        }
        if (focus) form.setFocus(focus);
        else setFormError(error.message);
      } else {
        setFormError("Something went wrong. Please try again.");
      }
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function onSubmit(values: Values) {
    if (values.status === "disabled" && tenant.status !== "disabled") {
      setPending(values);
      setOpen(false);
      setConfirming(true);
      return;
    }

    const ok = await save(values);
    if (ok) {
      setEditing(false);
      setNotice(`Saved changes to ${values.name}.`);
    }
  }

  async function confirmDisable() {
    if (!pending) return;
    const ok = await save(pending);
    setConfirming(false);
    setPending(null);
    if (!ok) {
      setEditing(true);
      setOpen(true);
    }
  }

  const status = form.watch("status");
  const nameError = form.formState.errors.name?.message;
  const emailError = form.formState.errors.admin_email?.message;

  return (
    <>
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={openDetails}>
          Details
        </Button>
        <span title="Coming in the next ticket" className="inline-flex">
          <Button variant="secondary" disabled>
            Work in this Tenant
          </Button>
        </span>
      </div>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent>
          <SheetHeader>
            <div className="flex flex-wrap items-center gap-2">
              <SheetTitle>
                {editing ? `Edit ${tenant.name}` : tenant.name}
              </SheetTitle>
              <StatusChip
                tone={tenant.status === "active" ? "success" : "danger"}
              >
                {tenant.status === "active" ? "Active" : "Disabled"}
              </StatusChip>
            </div>
            <SheetDescription>
              Data Source and Users are managed by the Tenant Admin.
            </SheetDescription>
          </SheetHeader>

          <SheetBody>
            {editing ? (
              <form
                id="edit-tenant"
                onSubmit={form.handleSubmit(onSubmit)}
                noValidate
              >
                <FormField id="edit-name" label="Tenant name" error={nameError}>
                  <Input
                    id="edit-name"
                    autoComplete="off"
                    aria-invalid={Boolean(nameError)}
                    aria-describedby={nameError ? "edit-name-error" : undefined}
                    {...form.register("name")}
                  />
                </FormField>

                <FormField
                  id="edit-admin-email"
                  label="Tenant Admin email"
                  error={emailError}
                >
                  <Input
                    id="edit-admin-email"
                    type="email"
                    autoComplete="off"
                    aria-invalid={Boolean(emailError)}
                    aria-describedby={
                      emailError ? "edit-admin-email-error" : undefined
                    }
                    {...form.register("admin_email")}
                  />
                </FormField>

                <fieldset className="mt-4">
                  <legend className="text-sm font-medium text-foreground">
                    Status
                  </legend>
                  <div className="mt-2 space-y-2">
                    {(["active", "disabled"] as const).map((value) => (
                      <label
                        key={value}
                        className={cn(
                          "flex cursor-pointer items-start gap-3 rounded-card border border-border px-3 py-3",
                          status === value && "border-primary bg-secondary",
                        )}
                      >
                        <input
                          type="radio"
                          value={value}
                          className="mt-0.5 h-5 w-5 accent-primary"
                          {...form.register("status")}
                        />
                        <span className="text-sm">
                          <span className="block font-medium text-foreground">
                            {value === "active" ? "Active" : "Disabled"}
                          </span>
                          <span className="block text-meta text-muted-foreground">
                            {value === "active"
                              ? "The Tenant can start its maintenance: connect its Data Source, set up the AI and add Users."
                              : "We no longer work with this Tenant. Its Users can’t sign in."}
                          </span>
                        </span>
                      </label>
                    ))}
                  </div>
                </fieldset>

                {formError && (
                  <p role="alert" className="mt-3 text-sm text-destructive">
                    {formError}
                  </p>
                )}
              </form>
            ) : (
              <>
                {notice && (
                  <p
                    role="status"
                    className="mb-4 rounded-control bg-secondary px-3 py-2 text-sm text-secondary-foreground"
                  >
                    {notice}
                  </p>
                )}
                <dl className="grid grid-cols-[130px_1fr] gap-x-3 gap-y-3 text-sm max-sm:grid-cols-1">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>
                    {tenant.status === "active"
                      ? "The Tenant can start its maintenance."
                      : "We no longer work with this Tenant. Its Users can’t sign in."}
                  </dd>
                  <dt className="text-muted-foreground">Data Source</dt>
                  <dd>
                    {tenant.data_source_state === "connected"
                      ? "Connected"
                      : "Not connected"}
                  </dd>
                  <dt className="text-muted-foreground">Tenant Admin</dt>
                  <dd className="break-words">
                    {tenant.admin_email ?? "No Tenant Admin email"}
                  </dd>
                  <dt className="text-muted-foreground">Users</dt>
                  <dd className="tabular-nums">{tenant.user_count}</dd>
                  <dt className="text-muted-foreground">Created</dt>
                  <dd>{monthYear(tenant.created_at)}</dd>
                </dl>
              </>
            )}
          </SheetBody>

          <SheetFooter>
            {editing ? (
              <>
                <Button
                  key="save"
                  type="submit"
                  form="edit-tenant"
                  disabled={saving}
                >
                  Save changes
                </Button>
                <Button
                  key="cancel-edit"
                  variant="secondary"
                  onClick={() => {
                    setEditing(false);
                    setFormError(null);
                  }}
                  disabled={saving}
                >
                  Cancel
                </Button>
              </>
            ) : (
              <>
                <Button
                  key="edit"
                  variant="secondary"
                  onClick={startEdit}
                >
                  Edit details
                </Button>
                <span title="Coming in the next ticket" className="inline-flex">
                  <Button variant="secondary" disabled>
                    Work in this Tenant
                  </Button>
                </span>
              </>
            )}
          </SheetFooter>
        </SheetContent>
      </Sheet>

      <AlertDialog open={confirming} onOpenChange={setConfirming}>
        <AlertDialogContent>
          <AlertDialogTitle>Disable {tenant.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            Users of this Tenant will not be able to sign in. Nothing is
            deleted.
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => void confirmDisable()}
              disabled={saving}
            >
              Disable Tenant
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}