"use client";

import { AlertTriangle, Loader2, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type FullscreenLoadingStateProps = {
  title?: string;
  description?: string;
};

type FullscreenErrorStateProps = {
  title?: string;
  description?: string;
  onRetry?: () => void;
};

export function FullscreenLoadingState({
  title = "Loading admin workspace...",
  description = "Preparing the current page and restoring your session.",
}: FullscreenLoadingStateProps) {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background p-6">
      <Card className="w-full max-w-md shadow-sm">
        <CardHeader className="text-center">
          <div className="mx-auto flex size-12 items-center justify-center rounded-full border bg-muted">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
          <CardTitle className="text-lg">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}

export function FullscreenErrorState({
  title = "Unable to load the admin interface",
  description = "A client-side error interrupted this page. Try loading it again.",
  onRetry,
}: FullscreenErrorStateProps) {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background p-6">
      <Card className="w-full max-w-md shadow-sm">
        <CardHeader className="text-center">
          <div className="mx-auto flex size-12 items-center justify-center rounded-full border border-destructive/20 bg-destructive/5">
            <AlertTriangle className="size-5 text-destructive" />
          </div>
          <CardTitle className="text-lg">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center gap-3">
          {onRetry ? (
            <Button onClick={onRetry}>
              <RefreshCcw className="mr-2 size-4" />
              Try Again
            </Button>
          ) : null}
          <Button variant="outline" onClick={() => window.location.reload()}>
            Reload Page
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
