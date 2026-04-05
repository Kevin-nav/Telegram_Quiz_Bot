"use client";

import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { ShieldCheck, Loader2 } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchAdminPrincipal, setAdminPassword } from "@/lib/api";

export default function SetPasswordPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const principalQuery = useQuery({
    queryKey: ["admin-principal"],
    queryFn: fetchAdminPrincipal,
    retry: false,
  });
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (principalQuery.isError) {
      router.replace("/login");
      return;
    }

    if (principalQuery.data && !principalQuery.data.must_change_password) {
      router.replace("/");
    }
  }, [principalQuery.data, principalQuery.isError, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation do not match.");
      return;
    }

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      const updatedPrincipal = await setAdminPassword(currentPassword, newPassword);
      queryClient.setQueryData(["admin-principal"], updatedPrincipal);
      router.replace("/");
      router.refresh();
    } catch {
      setError("Unable to update password right now.");
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        {/* Brand — matches login exactly */}
        <div className="mb-8 flex flex-col items-center gap-2">
          <div className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ShieldCheck className="size-5" />
          </div>
          <span className="text-lg font-semibold tracking-tight">Adarkwa Admin</span>
        </div>

        <Card className="border-border/50">
          <CardHeader className="space-y-1 text-center">
            <CardTitle className="text-xl">Set your password</CardTitle>
            <CardDescription>
              You were signed in with a temporary password. Choose a new one before continuing.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="currentPassword">Temporary password</Label>
                <Input
                  id="currentPassword"
                  name="currentPassword"
                  type="password"
                  placeholder="Enter your current password"
                  autoComplete="current-password"
                  autoFocus
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="newPassword">New password</Label>
                <Input
                  id="newPassword"
                  name="newPassword"
                  type="password"
                  placeholder="Create a new password"
                  autoComplete="new-password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="confirmPassword">Confirm password</Label>
                <Input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  placeholder="Repeat your new password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>

              {error && (
                <p className="text-sm text-destructive" role="alert">
                  {error}
                </p>
              )}

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 size-4 animate-spin" />
                    Updating...
                  </>
                ) : (
                  "Save password"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          This is a required security step.
        </p>
      </div>
    </div>
  );
}
