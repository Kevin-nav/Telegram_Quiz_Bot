"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { useQueryClient, useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import {
  adminApi,
  type AdminCatalogAccessEntry,
  type AdminStaffUser,
  type StaffFormValue,
} from "@/lib/api";
import { toast } from "sonner";

interface StaffSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  staff: AdminStaffUser | null;
}

const ROLE_OPTIONS = [
  {
    code: "super_admin",
    name: "Super Admin",
    description: "Full access across both bot workspaces.",
  },
  {
    code: "content_editor",
    name: "Content Editor",
    description: "Edit question content within the assigned bot.",
  },
  {
    code: "catalog_manager",
    name: "Catalog Manager",
    description: "Manage catalog offerings and active course availability.",
  },
  {
    code: "analytics_viewer",
    name: "Analytics Viewer",
    description: "Read-only access to reporting surfaces.",
  },
];

const PERMISSION_OPTIONS = [
  { code: "staff.view", name: "View staff" },
  { code: "staff.create", name: "Create staff" },
  { code: "staff.edit_permissions", name: "Edit permissions" },
  { code: "staff.reset_password", name: "Reset password" },
  { code: "catalog.view", name: "View catalog" },
  { code: "catalog.edit", name: "Edit catalog" },
  { code: "questions.view", name: "View questions" },
  { code: "questions.edit", name: "Edit questions" },
  { code: "questions.publish", name: "Publish questions" },
  { code: "analytics.view", name: "View analytics" },
  { code: "audit.view", name: "View audit log" },
];

const BOT_OPTIONS = [
  { code: "tanjah", name: "Tanjah" },
  { code: "adarkwa", name: "Adarkwa" },
];

function toPrettyCatalogJson(entries: AdminCatalogAccessEntry[]) {
  return JSON.stringify(entries, null, 2);
}

function parseCatalogAccessJson(raw: string, botAccess: string[]) {
  const trimmed = raw.trim();
  if (!trimmed) {
    return [];
  }

  const parsed = JSON.parse(trimmed);
  if (!Array.isArray(parsed)) {
    throw new Error("Catalog access must be a JSON array.");
  }

  return parsed.map((entry) => {
    if (!entry || typeof entry !== "object") {
      throw new Error("Each catalog access entry must be an object.");
    }

    const record = entry as Partial<AdminCatalogAccessEntry>;
    const botId = String(record.bot_id ?? "").trim();
    if (!botId) {
      throw new Error("Each catalog access entry needs a bot_id.");
    }
    if (!botAccess.includes(botId)) {
      throw new Error(`Catalog access bot_id must be one of: ${botAccess.join(", ")}.`);
    }

    return {
      bot_id: botId,
      program_code: String(record.program_code ?? "").trim() || null,
      level_code: String(record.level_code ?? "").trim() || null,
      course_code: String(record.course_code ?? "").trim() || null,
    };
  });
}

export function StaffSheet({ open, onOpenChange, staff }: StaffSheetProps) {
  const queryClient = useQueryClient();
  const isEditing = staff !== null;
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [tempPassword, setTempPassword] = useState("");
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [selectedBots, setSelectedBots] = useState<string[]>([]);
  const [catalogAccessJson, setCatalogAccessJson] = useState("[]");
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (staff) {
      setEmail(staff.email);
      setDisplayName(staff.display_name ?? "");
      setTempPassword("");
      setSelectedRoles(staff.role_codes);
      setSelectedPermissions(staff.permission_codes);
      setSelectedBots(staff.bot_access);
      setCatalogAccessJson(toPrettyCatalogJson(staff.catalog_access ?? []));
    } else {
      setEmail("");
      setDisplayName("");
      setTempPassword("");
      setSelectedRoles([]);
      setSelectedPermissions([]);
      setSelectedBots([]);
      setCatalogAccessJson("[]");
    }
    setLocalError(null);
  }, [staff, open]);

  const isSuperAdmin = useMemo(
    () => selectedRoles.includes("super_admin"),
    [selectedRoles],
  );

  function toggleRole(code: string) {
    setSelectedRoles((prev) =>
      prev.includes(code) ? prev.filter((role) => role !== code) : [...prev, code],
    );
  }

  function togglePermission(code: string) {
    setSelectedPermissions((prev) =>
      prev.includes(code)
        ? prev.filter((permission) => permission !== code)
        : [...prev, code],
    );
  }

  function toggleBot(code: string) {
    setSelectedBots((prev) =>
      prev.includes(code) ? prev.filter((bot) => bot !== code) : [...prev, code],
    );
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      const catalogAccess = parseCatalogAccessJson(catalogAccessJson, selectedBots);
      const payload: StaffFormValue = {
        email,
        display_name: displayName,
        is_active: staff?.is_active ?? true,
        role_codes: selectedRoles,
        permission_codes: selectedPermissions,
        bot_access: selectedBots,
        catalog_access: catalogAccess,
        temporary_password: isEditing ? undefined : tempPassword,
      };

      return adminApi.saveStaffUser(staff?.staff_user_id ?? null, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["staff-users"] });
      toast.success(isEditing ? "Staff user updated." : "Staff user created.");
      onOpenChange(false);
    },
    onError: (error) => {
      setLocalError(error instanceof Error ? error.message : "Unable to save staff user.");
    },
  });

  async function handleSave() {
    setLocalError(null);
    if (!isEditing && tempPassword.length < 8) {
      setLocalError("Temporary password must be at least 8 characters.");
      return;
    }

    if (!email.trim()) {
      setLocalError("Email is required.");
      return;
    }

    if (selectedBots.length === 0) {
      setLocalError("Select at least one bot workspace.");
      return;
    }

    saveMutation.mutate();
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>{isEditing ? "Edit Staff" : "Create Staff"}</SheetTitle>
          <SheetDescription>
            {isEditing
              ? `Update details for ${staff?.display_name ?? staff?.email}.`
              : "Add a new staff member to the admin platform."}
          </SheetDescription>
        </SheetHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="staff-email">Email</Label>
            <Input
              id="staff-email"
              type="email"
              placeholder="user@staff.adarkwa.edu"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="staff-name">Display Name</Label>
            <Input
              id="staff-name"
              placeholder="Full name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>
          {!isEditing && (
            <div className="grid gap-2">
              <Label htmlFor="staff-password">Temporary Password</Label>
              <Input
                id="staff-password"
                type="password"
                placeholder="Set initial password"
                value={tempPassword}
                onChange={(e) => setTempPassword(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                The user will be forced to change this on first login.
              </p>
            </div>
          )}

          <Separator />

          <div className="grid gap-3">
            <Label className="text-sm font-medium">Roles</Label>
            {ROLE_OPTIONS.map((role) => (
              <div key={role.code} className="flex items-start gap-3 rounded-lg border p-3">
                <Checkbox
                  id={`role-${role.code}`}
                  checked={selectedRoles.includes(role.code)}
                  onCheckedChange={() => toggleRole(role.code)}
                />
                <div className="grid gap-0.5">
                  <label htmlFor={`role-${role.code}`} className="cursor-pointer text-sm font-medium">
                    {role.name}
                  </label>
                  <p className="text-xs text-muted-foreground">{role.description}</p>
                </div>
              </div>
            ))}
          </div>

          <Separator />

          <div className="grid gap-3">
            <Label className="text-sm font-medium">Bot Access</Label>
            <div className="grid gap-2">
              {BOT_OPTIONS.map((bot) => (
                <div key={bot.code} className="flex items-center gap-2 rounded-lg border p-2.5">
                  <Checkbox
                    id={`bot-${bot.code}`}
                    checked={selectedBots.includes(bot.code)}
                    onCheckedChange={() => toggleBot(bot.code)}
                  />
                  <label htmlFor={`bot-${bot.code}`} className="cursor-pointer text-sm">
                    {bot.name}
                  </label>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              {isSuperAdmin
                ? "Super admins can select both bot workspaces."
                : "Non-super-admins should stay on one bot."}
            </p>
          </div>

          <Separator />

          <div className="grid gap-3">
            <Label className="text-sm font-medium">Permissions</Label>
            <div className="grid gap-2 sm:grid-cols-2">
              {PERMISSION_OPTIONS.map((permission) => (
                <div key={permission.code} className="flex items-center gap-2 rounded-lg border p-2.5">
                  <Checkbox
                    id={`perm-${permission.code}`}
                    checked={selectedPermissions.includes(permission.code)}
                    onCheckedChange={() => togglePermission(permission.code)}
                  />
                  <label htmlFor={`perm-${permission.code}`} className="cursor-pointer text-xs">
                    {permission.name}
                  </label>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          <div className="grid gap-2">
            <div className="flex items-center justify-between gap-2">
              <Label htmlFor="catalog-access">Catalog Access JSON</Label>
              <span className="text-xs text-muted-foreground">Optional</span>
            </div>
            <textarea
              id="catalog-access"
              className="min-h-40 rounded-md border bg-background px-3 py-2 text-sm font-mono outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              value={catalogAccessJson}
              onChange={(e) => setCatalogAccessJson(e.target.value)}
              placeholder={`[
  {
    "bot_id": "adarkwa",
    "program_code": "mechanical-engineering",
    "level_code": "100",
    "course_code": "calculus"
  }
]`}
            />
            <p className="text-xs text-muted-foreground">
              Provide a JSON array of scope objects. Leave it as `[]` for full access inside the assigned bot.
            </p>
          </div>

          {localError ? <p className="text-sm text-destructive">{localError}</p> : null}
        </div>

        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Saving...
              </>
            ) : isEditing ? (
              "Save Changes"
            ) : (
              "Create Staff"
            )}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
