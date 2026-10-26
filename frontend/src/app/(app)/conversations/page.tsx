import { Suspense } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getMe } from "@/lib/session";

export default function ConversationsPage() {
  return (
    <div className="mx-auto w-full max-w-[680px] pt-6 md:pt-16">
      <Suspense fallback={<GreetingFallback />}>
        <Greeting />
      </Suspense>
      <p className="mt-2 text-base text-muted-foreground">
        Ask in plain words. You get a live table.
      </p>

      <Card className="mt-8 p-4">
        <textarea
          disabled
          rows={2}
          aria-label="Your question"
          placeholder="Ask a question about your data"
          className="w-full resize-none rounded-control border border-input bg-card p-3 text-base text-foreground placeholder:text-muted-foreground disabled:opacity-60"
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <p className="text-meta text-muted-foreground">
            Coming in the next ticket.
          </p>
          <Button disabled>Ask</Button>
        </div>
      </Card>
    </div>
  );
}

function GreetingFallback() {
  return (
    <div
      aria-hidden="true"
      className="h-9 w-3/4 animate-pulse rounded-control bg-muted"
    />
  );
}

async function Greeting() {
  const me = await getMe();
  const firstName = me.user.full_name.split(" ")[0] || me.user.full_name;

  return (
    <h1 className="text-3xl font-semibold tracking-tight text-foreground">
      Hi {firstName}, what do you want to know?
    </h1>
  );
}