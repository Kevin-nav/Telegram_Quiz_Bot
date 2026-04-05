"use client";

import { useEffect } from "react";

import { FullscreenErrorState } from "@/components/app-fallbacks";

export default function Error({
  error,
  reset,
}: Readonly<{
  error: Error & { digest?: string };
  reset: () => void;
}>) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <FullscreenErrorState
      title="Unable to load this admin page"
      description="The page hit a client-side error during rendering or navigation."
      onRetry={reset}
    />
  );
}
