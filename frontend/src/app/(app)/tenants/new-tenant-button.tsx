"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button, buttonClasses } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { ApiError, apiFetch } from "@/lib/api";
import type { Tenant } from "@/lib/types";

const EMAIL_MESSAGE =
  "Enter the first Tenant Admin's email, like name@company.com.";

const schema = z.object({
  name: z.string().trim().min(1, "Enter a Tenant name."),
  admin_email: z
    .string()
    .trim()
    .min(1, EMAIL_MESSAGE)
    .regex(/^[^@\s]+@[^@\s]+$/, EMAIL_MESSAGE),
});

type Values = z.infer<typeof schema>;

export function NewTenantButton() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", admin_email: "" },
  });

  function changeOpen(next: boolean) {
    setOpen(next);
    if (!next) {
      form.reset();
      setFormError(null);
    }
  }

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const tenant = await apiFetch<Tenant>("/tenants", {
        method: "POST",
        body: JSON.stringify(values),
      });
      changeOpen(false);
      router.replace(`/tenants?created=${tenant.id}`);
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
    }
  }

  const nameError = form.formState.errors.name?.message;
  const emailError = form.formState.errors.admin_email?.message;

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger className={buttonClasses()}>New Tenant</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Tenant</DialogTitle>
          <DialogDescription>
            The first Tenant Admin can then connect the Data Source.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} noValidate>
          <FormField id="name" label="Tenant name" error={nameError}>
            <Input
              id="name"
              autoComplete="off"
              aria-invalid={Boolean(nameError)}
              aria-describedby={nameError ? "name-error" : undefined}
              {...form.register("name")}
            />
          </FormField>

          <FormField
            id="admin_email"
            label="First Tenant Admin email"
            error={emailError}
          >
            <Input
              id="admin_email"
              type="email"
              autoComplete="off"
              aria-invalid={Boolean(emailError)}
              aria-describedby={emailError ? "admin_email-error" : undefined}
              {...form.register("admin_email")}
            />
          </FormField>

          {formError && (
            <p role="alert" className="mt-3 text-sm text-destructive">
              {formError}
            </p>
          )}

          <DialogFooter>
            <DialogClose className={buttonClasses({ variant: "secondary" })}>
              Cancel
            </DialogClose>
            <Button
              type="submit"
              disabled={form.formState.isSubmitting}
            >
              Create Tenant
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}