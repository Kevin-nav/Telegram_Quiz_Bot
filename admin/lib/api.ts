const DEFAULT_ADMIN_API_BASE_URL = process.env.NEXT_PUBLIC_ADMIN_API_BASE_URL ?? "";

function normalizeBaseUrl(baseUrl: string) {
  return baseUrl.replace(/\/+$/, "");
}

function buildUrl(path: string) {
  if (/^https?:\/\//.test(path)) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const baseUrl = normalizeBaseUrl(DEFAULT_ADMIN_API_BASE_URL);
  return `${baseUrl}${normalizedPath}`;
}

export async function adminFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(buildUrl(path), {
    ...init,
    credentials: "include",
    headers,
  });

  if (!response.ok) {
    throw new Error(`Admin request failed: ${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export const adminApi = {
  buildUrl,
  fetch: adminFetch,
};
