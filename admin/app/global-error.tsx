"use client";

import { useEffect } from "react";

import { FullscreenErrorState } from "@/components/app-fallbacks";

export default function GlobalError({
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
    <html lang="en">
      <body>
        <FullscreenErrorState
          title="Admin app failed to initialize"
          description="A global client-side error interrupted the admin interface before the page could render."
          onRetry={reset}
        />
      </body>
    </html>
  );
}
