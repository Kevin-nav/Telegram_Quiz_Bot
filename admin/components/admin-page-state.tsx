"use client";

import type { ReactNode } from "react";
import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";

import { AdminShell } from "@/components/admin-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type AdminPageStateProps = {
  title: string;
  description: string;
  message: string;
  action?: ReactNode;
};

export function AdminLoadingState({
  title,
  description,
  message,
}: AdminPageStateProps) {
  return (
    <AdminShell>
      <div className="space-y-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        <Card>
          <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 py-12 text-center">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">{message}</p>
          </CardContent>
        </Card>
      </div>
    </AdminShell>
  );
}

export function AdminErrorState({
  title,
  description,
  message,
  action,
}: AdminPageStateProps) {
  return (
    <AdminShell>
      <div className="space-y-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        <Card>
          <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 py-12 text-center">
            <div className="flex size-10 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <AlertTriangle className="size-5" />
            </div>
            <p className="max-w-md text-sm text-muted-foreground">{message}</p>
            {action ?? null}
          </CardContent>
        </Card>
      </div>
    </AdminShell>
  );
}

export function AdminRetryButton({
  onClick,
  isPending = false,
  label = "Try again",
}: {
  onClick: () => void;
  isPending?: boolean;
  label?: string;
}) {
  return (
    <Button variant="outline" onClick={onClick} disabled={isPending}>
      <RefreshCw className={`mr-2 size-4 ${isPending ? "animate-spin" : ""}`} />
      {label}
    </Button>
  );
}
