"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchAdminPrincipal } from "@/lib/api";
import { adminQueryKeys } from "@/lib/query-keys";

export function useAdminPrincipal() {
  return useQuery({
    queryKey: adminQueryKeys.principal(),
    queryFn: fetchAdminPrincipal,
    retry: false,
    staleTime: 5 * 60_000,
  });
}
