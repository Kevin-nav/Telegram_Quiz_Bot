import { FullscreenLoadingState } from "@/components/app-fallbacks";

export default function Loading() {
  return (
    <FullscreenLoadingState
      title="Loading admin page..."
      description="Please wait while the next workspace view is prepared."
    />
  );
}
