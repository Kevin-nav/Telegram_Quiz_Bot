"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Users,
  FolderTree,
  FileQuestion,
  BarChart3,
  Inbox,
  LogOut,
  ShieldCheck,
  ChevronsUpDown,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { FullscreenLoadingState } from "@/components/app-fallbacks";
import { CommandPalette } from "@/components/command-palette";
import { BotWorkspaceSwitcher } from "@/components/bot-workspace-switcher";
import { fetchAdminPrincipal, logoutAdmin } from "@/lib/api";
import { toast } from "sonner";

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard, permission: null },
  { href: "/staff", label: "Staff", icon: Users, permission: "staff.view" },
  { href: "/catalog", label: "Catalog", icon: FolderTree, permission: "catalog.view" },
  { href: "/questions", label: "Questions", icon: FileQuestion, permission: "questions.view" },
  { href: "/analytics", label: "Analytics", icon: BarChart3, permission: "analytics.view" },
  { href: "/reports", label: "Reports", icon: Inbox, permission: "audit.view" },
];

function getInitials(name: string) {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function getPageTitle(pathname: string | null | undefined) {
  if (pathname === "/") return "Overview";
  if (!pathname) return "Admin";
  const item = navItems.find((n) => pathname.startsWith(n.href) && n.href !== "/");
  return item?.label ?? "Admin";
}

export function AdminShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const safePathname = pathname ?? "";
  const router = useRouter();
  const queryClient = useQueryClient();
  const principalQuery = useQuery({
    queryKey: ["admin-principal"],
    queryFn: fetchAdminPrincipal,
    retry: false,
  });
  const principal = principalQuery.data ?? null;
  const mustRedirectToPassword =
    principal?.must_change_password === true && safePathname !== "/set-password";

  useEffect(() => {
    if (principalQuery.isError) {
      router.replace("/login");
      return;
    }

    if (mustRedirectToPassword) {
      router.replace("/set-password");
    }
  }, [mustRedirectToPassword, principalQuery.isError, router]);

  async function handleLogout() {
    try {
      await logoutAdmin();
    } catch {
      // Continue the local sign-out flow even if the server already expired.
    } finally {
      queryClient.clear();
      await router.replace("/login");
      router.refresh();
      toast.success("Signed out.");
    }
  }

  if (!principal && principalQuery.isLoading) {
    return (
      <FullscreenLoadingState
        title="Loading admin workspace..."
        description="Checking your session and workspace permissions."
      />
    );
  }

  if (!principal && principalQuery.isError) {
    return (
      <FullscreenLoadingState
        title="Redirecting to sign in..."
        description="Your session could not be restored for this page."
      />
    );
  }

  if (mustRedirectToPassword) {
    return (
      <FullscreenLoadingState
        title="Password update required"
        description="Redirecting you to set a new password before continuing."
      />
    );
  }

  const visibleNavItems = navItems.filter((item) => {
    if (!item.permission) {
      return true;
    }
    return principal?.permission_codes?.includes(item.permission) ?? false;
  });

  return (
    <SidebarProvider>
      <Sidebar variant="sidebar" collapsible="icon">
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" render={<Link href="/" />}>
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <ShieldCheck className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">Adarkwa</span>
                  <span className="truncate text-xs text-muted-foreground">Admin Console</span>
                </div>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        <SidebarSeparator />

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Platform</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {visibleNavItems.map((item) => {
                  const isActive =
                    item.href === "/"
                      ? safePathname === "/"
                      : safePathname.startsWith(item.href);
                  return (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton
                        isActive={isActive}
                        tooltip={item.label}
                        render={<Link href={item.href} />}
                      >
                        <item.icon className="size-4" />
                        <span>{item.label}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <SidebarMenuButton
                      size="lg"
                      className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                    >
                      <Avatar className="size-8 rounded-lg">
                        <AvatarFallback className="rounded-lg text-xs">
                          {getInitials(principal?.display_name ?? "Admin")}
                        </AvatarFallback>
                      </Avatar>
                      <div className="grid flex-1 text-left text-sm leading-tight">
                        <span className="truncate font-semibold">
                          {principal?.display_name ?? "Admin"}
                        </span>
                        <span className="truncate text-xs text-muted-foreground">
                          {principal?.role_codes?.[0]?.replace("_", " ") ?? "staff"}
                        </span>
                      </div>
                      <ChevronsUpDown className="ml-auto size-4" />
                    </SidebarMenuButton>
                  }
                />
                <DropdownMenuContent
                  className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                  side="bottom"
                  align="end"
                  sideOffset={4}
                >
                  <DropdownMenuLabel className="p-0 font-normal">
                    <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                      <Avatar className="size-8 rounded-lg">
                        <AvatarFallback className="rounded-lg text-xs">
                          {getInitials(principal?.display_name ?? "Admin")}
                        </AvatarFallback>
                      </Avatar>
                      <div className="grid flex-1 text-left text-sm leading-tight">
                        <span className="truncate font-semibold">{principal?.display_name ?? "Admin"}</span>
                        <span className="truncate text-xs text-muted-foreground">
                          {principal?.email ?? "staff"}
                        </span>
                        {principal?.active_bot_id ? (
                          <span className="truncate text-[11px] text-muted-foreground">
                            {principal.active_bot_id}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout}>
                    <LogOut className="mr-2 size-4" />
                    Log Out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>

      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <h1 className="text-sm font-medium">{getPageTitle(pathname)}</h1>
          <div className="ml-auto flex items-center gap-2">
            {principal ? <BotWorkspaceSwitcher principal={principal} /> : null}
            <CommandPalette />
          </div>
        </header>
        <div className="flex-1 overflow-auto">
          <div className="animate-in-page p-4 md:p-6">{children}</div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
