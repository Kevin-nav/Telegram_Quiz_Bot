"use client";

import { useState } from "react";
import {
  MoreHorizontal,
  Plus,
  KeyRound,
  UserX,
  UserCheck,
  Search,
  Loader2,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AdminShell } from "@/components/admin-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { StaffSheet } from "@/components/staff/staff-sheet";
import {
  listStaffUsers,
  resetStaffPassword,
  saveStaffUser,
  type AdminStaffUser,
} from "@/lib/api";
import { toast } from "sonner";

const BOT_LABELS: Record<string, string> = {
  tanjah: "Tanjah",
  adarkwa: "Adarkwa",
};

function displayBotAccess(botAccess: string[]) {
  return botAccess.map((botId) => BOT_LABELS[botId] ?? botId);
}

export default function StaffPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editingStaff, setEditingStaff] = useState<AdminStaffUser | null>(null);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState<AdminStaffUser | null>(null);
  const [resetPassword, setResetPassword] = useState("");

  const staffQuery = useQuery({
    queryKey: ["staff-users"],
    queryFn: listStaffUsers,
  });

  const staff = staffQuery.data ?? [];
  const searchValue = search.toLowerCase();
  const filtered = staff.filter((s) => {
    return (
      (s.display_name ?? "").toLowerCase().includes(searchValue) ||
      s.email.toLowerCase().includes(searchValue) ||
      s.role_codes.join(" ").toLowerCase().includes(searchValue) ||
      s.bot_access.join(" ").toLowerCase().includes(searchValue)
    );
  });

  const toggleActiveMutation = useMutation({
    mutationFn: async (user: AdminStaffUser) =>
      saveStaffUser(user.staff_user_id, {
        email: user.email,
        display_name: user.display_name ?? "",
        is_active: !user.is_active,
        role_codes: user.role_codes,
        permission_codes: user.permission_codes,
        bot_access: user.bot_access,
        catalog_access: user.catalog_access ?? [],
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["staff-users"] });
      toast.success("Staff user updated.");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Unable to update staff user.");
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: async () => {
      if (!resetTarget) {
        throw new Error("No staff user selected.");
      }
      return resetStaffPassword(resetTarget.staff_user_id, resetPassword);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["staff-users"] });
      toast.success("Temporary password issued.");
      setResetDialogOpen(false);
      setResetTarget(null);
      setResetPassword("");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Unable to reset password.");
    },
  });

  function handleCreate() {
    setEditingStaff(null);
    setSheetOpen(true);
  }

  function handleEdit(user: AdminStaffUser) {
    setEditingStaff(user);
    setSheetOpen(true);
  }

  function handleResetPassword(user: AdminStaffUser) {
    setResetTarget(user);
    setResetPassword("");
    setResetDialogOpen(true);
  }

  return (
    <AdminShell>
      <div className="space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Staff</h2>
            <p className="text-sm text-muted-foreground">
              Manage team members, bot access, and permissions.
            </p>
          </div>
          <Button onClick={handleCreate}>
            <Plus className="mr-2 size-4" />
            Create Staff
          </Button>
        </div>

        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name, email, role, or bot..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Roles</TableHead>
                <TableHead>Bots</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {staffQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                    <Loader2 className="mx-auto mb-2 size-5 animate-spin" />
                    Loading staff...
                  </TableCell>
                </TableRow>
              ) : staffQuery.isError ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-destructive">
                    Unable to load staff.
                  </TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                    No staff members found.
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((user) => (
                  <TableRow key={user.staff_user_id}>
                    <TableCell className="font-medium">
                      <div className="grid gap-1">
                        <span>{user.display_name || "Unnamed staff"}</span>
                        {user.must_change_password ? (
                          <span className="text-xs text-muted-foreground">Temporary password pending</span>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{user.email}</TableCell>
                    <TableCell>
                      <Badge variant={user.is_active ? "default" : "secondary"}>
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {user.role_codes.map((role) => (
                          <Badge key={role} variant="outline" className="text-xs">
                            {role.replace("_", " ")}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {displayBotAccess(user.bot_access).map((bot) => (
                          <Badge key={bot} variant="secondary" className="text-xs">
                            {bot}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            render={<Button variant="ghost" size="icon" className="size-8" />}
                          >
                            <MoreHorizontal className="size-4" />
                            <span className="sr-only">Actions</span>
                          </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEdit(user)}>
                            Edit details
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => toggleActiveMutation.mutate(user)}
                            disabled={toggleActiveMutation.isPending}
                          >
                            {user.is_active ? (
                              <>
                                <UserX className="mr-2 size-4" />
                                Deactivate
                              </>
                            ) : (
                              <>
                                <UserCheck className="mr-2 size-4" />
                                Activate
                              </>
                            )}
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => handleResetPassword(user)}
                          >
                            <KeyRound className="mr-2 size-4" />
                            Reset Password
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <StaffSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        staff={editingStaff}
      />

      <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive">Reset Password</DialogTitle>
            <DialogDescription>
              This will invalidate all active sessions for{" "}
              <strong>{resetTarget?.display_name ?? resetTarget?.email}</strong> and issue a new temporary password.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="reset-password">Temporary password</Label>
            <Input
              id="reset-password"
              type="password"
              value={resetPassword}
              onChange={(e) => setResetPassword(e.target.value)}
              placeholder="Enter a new temporary password"
            />
          </div>
          <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3">
            <p className="text-sm text-destructive">
              This action logs the user out of all devices immediately.
            </p>
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setResetDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => resetPasswordMutation.mutate()}
              disabled={!resetPassword || resetPasswordMutation.isPending}
            >
              {resetPasswordMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  Resetting...
                </>
              ) : (
                "Reset Password"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminShell>
  );
}
