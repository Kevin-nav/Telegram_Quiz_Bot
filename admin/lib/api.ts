const DEFAULT_ADMIN_API_BASE_URL = process.env.NEXT_PUBLIC_ADMIN_API_BASE_URL ?? "";

export type AdminPrincipal = {
  staff_user_id: number;
  email: string;
  display_name: string | null;
};

export type AdminRole = {
  code: string;
  name: string;
  description: string | null;
};

export type AdminPermission = {
  code: string;
  name: string;
  description: string | null;
};

export type AdminStaffUser = {
  id: number;
  email: string;
  display_name: string | null;
  is_active: boolean;
  roles: string[];
  permissions: string[];
};

export type StaffFormValue = {
  email: string;
  display_name: string;
  is_active: boolean;
  role_codes: string[];
};

export type CatalogQuery = {
  faculty_code?: string;
  program_code?: string;
  level_code?: string;
  semester_code?: string;
};

export type CatalogItem = {
  code: string;
  name: string;
  active?: boolean;
  level_code?: string;
  semester_code?: string;
};

export type CatalogNode = {
  kind: "faculty" | "program" | "level" | "semester" | "course";
  code: string;
  name: string;
  active?: boolean;
  children: CatalogNode[];
};

export type CatalogOfferingValue = {
  faculty_code: string;
  program_code: string;
  level_code: string;
  semester_code: string;
  course_code: string;
  is_active: boolean;
};

export type QuestionRecord = {
  id: number;
  question_key: string;
  course_id: string;
  course_slug: string;
  question_text: string;
  options: string[];
  correct_option_text: string;
  short_explanation: string | null;
  question_type: string;
  option_count: number;
  status: string;
  band: number;
  topic_id: string;
  cognitive_level: string | null;
  updated_at: string | null;
};

export type QuestionDraft = {
  question_text: string;
  options_text: string;
  correct_option_text: string;
  short_explanation: string;
  question_type: string;
  status: string;
  band: number;
  topic_id: string;
  cognitive_level: string;
};

export type AuditLogEntry = {
  id: number;
  actor_staff_user_id: number | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before_data: Record<string, unknown> | null;
  after_data: Record<string, unknown> | null;
  created_at: string;
};

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

function readCookie(name: string) {
  if (typeof document === "undefined") {
    return null;
  }

  const cookies = document.cookie.split(";").map((entry) => entry.trim());
  const match = cookies.find((entry) => entry.startsWith(`${name}=`));
  if (!match) {
    return null;
  }
  return decodeURIComponent(match.slice(name.length + 1));
}

function resolveAdminUserId() {
  const sessionId = readCookie("admin_session");
  if (!sessionId || !/^\d+$/.test(sessionId)) {
    return null;
  }
  return sessionId;
}

function buildHeaders(init: RequestInit["headers"], body: BodyInit | null | undefined) {
  const headers = new Headers(init);
  if (body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const adminUserId = resolveAdminUserId();
  if (adminUserId && !headers.has("X-Admin-User-Id")) {
    headers.set("X-Admin-User-Id", adminUserId);
  }

  return headers;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  return (await response.text()) as T;
}

export async function adminFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(buildUrl(path), {
    ...init,
    credentials: "include",
    headers: buildHeaders(init.headers, init.body),
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      if (typeof payload === "string") {
        detail = payload;
      } else if (payload && typeof payload === "object" && "detail" in payload) {
        detail = String((payload as { detail: unknown }).detail);
      }
    } catch {
      const text = await response.text().catch(() => "");
      if (text) {
        detail = text;
      }
    }

    throw new Error(`Admin request failed: ${response.status} ${detail}`);
  }

  return parseResponse<T>(response);
}

function normalizeListResponse<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) {
    return payload as T[];
  }

  if (payload && typeof payload === "object" && "items" in payload) {
    const items = (payload as { items?: unknown }).items;
    if (Array.isArray(items)) {
      return items as T[];
    }
  }

  return [];
}

function normalizeObjectResponse<T>(payload: unknown): T | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return null;
  }

  return payload as T;
}

function queryString(query: CatalogQuery) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) {
      params.set(key, value);
    }
  }
  const suffix = params.toString();
  return suffix ? `?${suffix}` : "";
}

export async function fetchAdminPrincipal() {
  return adminFetch<AdminPrincipal>("/admin/auth/me");
}

export async function listStaffUsers() {
  const payload = await adminFetch<unknown>("/admin/staff");
  return normalizeListResponse<AdminStaffUser>(payload);
}

export async function getStaffUser(staffUserId: number) {
  const payload = await adminFetch<unknown>(`/admin/staff/${staffUserId}`);
  return normalizeObjectResponse<AdminStaffUser>(payload);
}

export async function saveStaffUser(
  staffUserId: number | null,
  payload: StaffFormValue,
) {
  const path = staffUserId === null ? "/admin/staff" : `/admin/staff/${staffUserId}`;
  const method = staffUserId === null ? "POST" : "PATCH";
  return adminFetch<AdminStaffUser>(path, {
    method,
    body: JSON.stringify(payload),
  });
}

export async function updateStaffPermissions(
  staffUserId: number,
  permissionCodes: string[],
) {
  return adminFetch<{ permissions: string[] }>(`/admin/staff/${staffUserId}/permissions`, {
    method: "PUT",
    body: JSON.stringify({ permission_codes: permissionCodes }),
  });
}

export async function listCatalogItems(query: CatalogQuery = {}) {
  const payload = await adminFetch<unknown>(`/admin/catalog${queryString(query)}`);
  const response = normalizeObjectResponse<{ kind: string; items: CatalogItem[] }>(payload);
  return response ?? { kind: "faculties", items: [] };
}

export async function fetchCatalogTree(): Promise<CatalogNode[]> {
  const faculties = await listCatalogItems();
  const facultyNodes = await Promise.all(
    faculties.items.map(async (faculty) => {
      const programs = await listCatalogItems({ faculty_code: faculty.code });
      const programNodes = await Promise.all(
        programs.items.map(async (program) => {
          const levels = await listCatalogItems({
            faculty_code: faculty.code,
            program_code: program.code,
          });
          const levelNodes = await Promise.all(
            levels.items.map(async (level) => {
              const semesters = await listCatalogItems({
                faculty_code: faculty.code,
                program_code: program.code,
                level_code: level.code,
              });
              const semesterNodes = await Promise.all(
                semesters.items.map(async (semester) => {
                  const courses = await listCatalogItems({
                    faculty_code: faculty.code,
                    program_code: program.code,
                    level_code: level.code,
                    semester_code: semester.code,
                  });
                  return {
                    kind: "semester" as const,
                    code: semester.code,
                    name: semester.name,
                    active: semester.active ?? true,
                    children: courses.items.map((course) => ({
                      kind: "course" as const,
                      code: course.code,
                      name: course.name,
                      active: course.active ?? true,
                      children: [],
                    })),
                  };
                }),
              );
              return {
                kind: "level" as const,
                code: level.code,
                name: level.name,
                active: level.active ?? true,
                children: semesterNodes,
              };
            }),
          );
          return {
            kind: "program" as const,
            code: program.code,
            name: program.name,
            active: program.active ?? true,
            children: levelNodes,
          };
        }),
      );
      return {
        kind: "faculty" as const,
        code: faculty.code,
        name: faculty.name,
        active: faculty.active ?? true,
        children: programNodes,
      };
    }),
  );

  return facultyNodes;
}

export async function saveCatalogOffering(payload: CatalogOfferingValue) {
  return adminFetch<{ ok: boolean; item?: CatalogOfferingValue }>("/admin/catalog/offerings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listQuestions() {
  const payload = await adminFetch<unknown>("/admin/questions");
  return normalizeListResponse<QuestionRecord>(payload);
}

export async function saveQuestion(questionId: number | null, payload: QuestionDraft) {
  const path = questionId === null ? "/admin/questions" : `/admin/questions/${questionId}`;
  const method = questionId === null ? "POST" : "PATCH";
  const body = {
    ...payload,
    options: payload.options_text
      .split("\n")
      .map((option) => option.trim())
      .filter(Boolean),
  };

  return adminFetch<QuestionRecord>(path, {
    method,
    body: JSON.stringify(body),
  });
}

export async function listAuditLogs() {
  const payload = await adminFetch<unknown>("/admin/audit");
  return normalizeListResponse<AuditLogEntry>(payload);
}

export const adminApi = {
  buildUrl,
  fetch: adminFetch,
  fetchAdminPrincipal,
  fetchCatalogTree,
  getStaffUser,
  listAuditLogs,
  listCatalogItems,
  listQuestions,
  listStaffUsers,
  saveCatalogOffering,
  saveQuestion,
  saveStaffUser,
  updateStaffPermissions,
};
