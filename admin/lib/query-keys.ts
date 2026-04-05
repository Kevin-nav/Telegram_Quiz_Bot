export const adminQueryKeys = {
  principal: () => ["admin-principal"] as const,
  staffUsers: () => ["staff-users"] as const,
  catalogTree: (botId: string | null | undefined) =>
    ["catalog-tree", botId ?? "unscoped"] as const,
  questions: (botId: string | null | undefined) =>
    ["questions", botId ?? "unscoped"] as const,
  analytics: (botId: string | null | undefined) =>
    ["analytics", botId ?? "unscoped"] as const,
  studentAnalytics: (botId: string | null | undefined, userId: number) =>
    ["analytics", botId ?? "unscoped", "students", userId] as const,
  reports: (botId: string | null | undefined, status?: string | null) =>
    ["reports", botId ?? "unscoped", status ?? "all"] as const,
};
