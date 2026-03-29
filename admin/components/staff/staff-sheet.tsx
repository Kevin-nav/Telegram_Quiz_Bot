"use client";

import { useState, useEffect } from "react";
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
import { MOCK_ROLES, MOCK_PERMISSIONS, type StaffUser } from "@/lib/mock-data";
import { Loader2 } from "lucide-react";

interface StaffSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  staff: StaffUser | null;
}

export function StaffSheet({ open, onOpenChange, staff }: StaffSheetProps) {
  const isEditing = staff !== null;
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [tempPassword, setTempPassword] = useState("");
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (staff) {
      setEmail(staff.email);
      setDisplayName(staff.display_name);
      setTempPassword("");
      setSelectedRoles(staff.roles);
      setSelectedPermissions(staff.permissions);
    } else {
      setEmail("");
      setDisplayName("");
      setTempPassword("");
      setSelectedRoles([]);
      setSelectedPermissions([]);
    }
  }, [staff, open]);

  function toggleRole(code: string) {
    setSelectedRoles((prev) =>
      prev.includes(code) ? prev.filter((r) => r !== code) : [...prev, code],
    );
  }

  function togglePermission(code: string) {
    setSelectedPermissions((prev) =>
      prev.includes(code) ? prev.filter((p) => p !== code) : [...prev, code],
    );
  }

  async function handleSave() {
    setIsSaving(true);
    // TODO: Wire to API
    await new Promise((resolve) => setTimeout(resolve, 800));
    setIsSaving(false);
    onOpenChange(false);
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{isEditing ? "Edit Staff" : "Create Staff"}</SheetTitle>
          <SheetDescription>
            {isEditing
              ? `Update details for ${staff?.display_name}.`
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

          {/* Roles */}
          <div className="grid gap-3">
            <Label className="text-sm font-medium">Roles</Label>
            {MOCK_ROLES.map((role) => (
              <div key={role.code} className="flex items-start gap-3 rounded-lg border p-3">
                <Checkbox
                  id={`role-${role.code}`}
                  checked={selectedRoles.includes(role.code)}
                  onCheckedChange={() => toggleRole(role.code)}
                />
                <div className="grid gap-0.5">
                  <label htmlFor={`role-${role.code}`} className="text-sm font-medium cursor-pointer">
                    {role.name}
                  </label>
                  <p className="text-xs text-muted-foreground">{role.description}</p>
                </div>
              </div>
            ))}
          </div>

          <Separator />

          {/* Permissions Matrix */}
          <div className="grid gap-3">
            <Label className="text-sm font-medium">Permissions</Label>
            <div className="grid gap-2 sm:grid-cols-2">
              {MOCK_PERMISSIONS.map((perm) => (
                <div key={perm.code} className="flex items-center gap-2 rounded-lg border p-2.5">
                  <Checkbox
                    id={`perm-${perm.code}`}
                    checked={selectedPermissions.includes(perm.code)}
                    onCheckedChange={() => togglePermission(perm.code)}
                  />
                  <label htmlFor={`perm-${perm.code}`} className="text-xs cursor-pointer">
                    {perm.name}
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>

        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? (
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
