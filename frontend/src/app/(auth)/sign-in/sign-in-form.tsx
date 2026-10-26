"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronDown } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, apiFetch } from "@/lib/api";
import type { PublicTenant } from "@/lib/types";

const schema = z.object({
  tenant: z.string().min(1, "Choose a Tenant."),
  email: z.string().trim().min(1, "Enter your email."),
});

type SignInValues = z.infer<typeof schema>;

type SignInFormProps = {
  tenants: PublicTenant[];
  tenantsUnavailable: boolean;
};

export function SignInForm({ tenants, tenantsUnavailable }: SignInFormProps) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<SignInValues>({
    resolver: zodResolver(schema),
    defaultValues: { tenant: "", email: "" },
  });

  async function onSubmit(values: SignInValues) {
    setFormError(null);
    try {
      await apiFetch("/auth/sign-in", {
        method: "POST",
        body: JSON.stringify(values),
      });
      router.replace("/conversations");
    } catch (error) {
      if (!(error instanceof ApiError)) {
        setFormError("Something went wrong. Please try again.");
        return;
      }

      if (error.code === "unknown_email") {
        setError("email", { message: error.message });
        return;
      }

      let mapped = false;
      for (const [field, message] of Object.entries(error.fields ?? {})) {
        if (field.startsWith("tenant")) {
          setError("tenant", { message });
          mapped = true;
        } else if (field === "email") {
          setError("email", { message });
          mapped = true;
        }
      }
      if (!mapped) setFormError(error.message);
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-background px-4 py-16">
      <div className="w-full max-w-[420px]">
        <p className="mb-6 text-xl font-semibold text-primary">Chattics</p>

        <Card className="p-6 md:p-8">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            Sign in
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Ask questions about your business data.
          </p>

          <p className="mt-4 rounded-control bg-secondary px-3 py-2 text-meta text-secondary-foreground">
            Test mode: no password needed. This login is switched off in live
            environments.
          </p>

          <form
            noValidate
            onSubmit={handleSubmit(onSubmit)}
            className="mt-6 space-y-4"
          >
            {formError && (
              <p
                role="alert"
                className="rounded-control border border-destructive/40 bg-danger-bg px-3 py-2 text-sm text-destructive"
              >
                {formError}
              </p>
            )}

            <div>
              <Label htmlFor="tenant">Tenant</Label>
              <div className="relative mt-1.5">
                <select
                  id="tenant"
                  {...register("tenant")}
                  aria-invalid={errors.tenant ? true : undefined}
                  aria-describedby={errors.tenant ? "tenant-error" : undefined}
                  className="h-11 w-full appearance-none rounded-control border border-input bg-card px-3 pr-10 text-base text-foreground aria-invalid:border-destructive"
                >
                  <option value="" disabled>
                    Choose…
                  </option>
                  {tenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.name}
                    </option>
                  ))}
                  <option value="platform">Platform</option>
                </select>
                <ChevronDown
                  aria-hidden="true"
                  className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                />
              </div>
              {errors.tenant && (
                <p
                  id="tenant-error"
                  role="alert"
                  className="mt-1.5 text-meta text-destructive"
                >
                  {errors.tenant.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="off"
                placeholder="you@company.com"
                className="mt-1.5"
                {...register("email")}
                aria-invalid={errors.email ? true : undefined}
                aria-describedby={errors.email ? "email-error" : undefined}
              />
              {errors.email && (
                <p
                  id="email-error"
                  role="alert"
                  className="mt-1.5 text-meta text-destructive"
                >
                  {errors.email.message}
                </p>
              )}
            </div>

            {tenantsUnavailable && (
              <p role="alert" className="text-meta text-destructive">
                Tenants could not be loaded. Reload the page.
              </p>
            )}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </Card>
      </div>
    </main>
  );
}