"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  LayoutDashboard,
  Users,
  FolderTree,
  FileQuestion,
  BarChart3,
  Inbox,
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import {
  fetchCatalogTree,
  listQuestions,
  listStaffUsers,
  type CatalogNode,
} from "@/lib/api";

const pages = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Staff Management", href: "/staff", icon: Users },
  { label: "Catalog", href: "/catalog", icon: FolderTree },
  { label: "Questions", href: "/questions", icon: FileQuestion },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Reports", href: "/reports", icon: Inbox },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const staffQuery = useQuery({
    queryKey: ["staff-users"],
    queryFn: listStaffUsers,
    enabled: open,
    retry: false,
  });
  const catalogTreeQuery = useQuery({
    queryKey: ["catalog-tree"],
    queryFn: fetchCatalogTree,
    enabled: open,
    retry: false,
  });
  const questionsQuery = useQuery({
    queryKey: ["questions"],
    queryFn: listQuestions,
    enabled: open,
    retry: false,
  });

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const runCommand = useCallback(
    (command: () => void) => {
      setOpen(false);
      command();
    },
    [],
  );

  const courses = useMemo(() => {
    const flattened: { code: string; name: string }[] = [];

    function extractCourses(entries: CatalogNode[]) {
      for (const entry of entries) {
        if (entry.kind === "course") {
          flattened.push({ code: entry.code, name: entry.name });
          continue;
        }
        if (entry.children.length > 0) {
          extractCourses(entry.children);
        }
      }
    }

    extractCourses(catalogTreeQuery.data ?? []);
    return flattened;
  }, [catalogTreeQuery.data]);

  const staff = staffQuery.data ?? [];
  const questions = questionsQuery.data ?? [];

  return (
    <>
      <Button
        variant="outline"
        className="relative h-8 w-full justify-start rounded-md bg-muted/50 px-3 text-sm font-normal text-muted-foreground shadow-none sm:w-64"
        onClick={() => setOpen(true)}
      >
        <Search className="mr-2 size-4" />
        <span className="hidden lg:inline-flex">Search everything...</span>
        <span className="inline-flex lg:hidden">Search...</span>
        <kbd className="pointer-events-none absolute right-1.5 top-1.5 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </Button>

      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder="Search pages, staff, courses, questions..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>

          <CommandGroup heading="Pages">
            {pages.map((page) => (
              <CommandItem
                key={page.href}
                onSelect={() => runCommand(() => router.push(page.href))}
              >
                <page.icon className="mr-2 size-4" />
                <span>{page.label}</span>
              </CommandItem>
            ))}
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Staff">
            {staff.map((staff) => (
              <CommandItem
                key={staff.staff_user_id}
                onSelect={() => runCommand(() => router.push("/staff"))}
              >
                <Users className="mr-2 size-4" />
                <span>{staff.display_name ?? staff.email}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {staff.email}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Courses">
            {courses.map((course) => (
              <CommandItem
                key={course.code}
                onSelect={() => runCommand(() => router.push("/catalog"))}
              >
                <FolderTree className="mr-2 size-4" />
                <span>{course.name}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {course.code}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Questions">
            {questions.slice(0, 5).map((q) => (
              <CommandItem
                key={q.question_key}
                onSelect={() => runCommand(() => router.push("/questions"))}
              >
                <FileQuestion className="mr-2 size-4" />
                <span className="truncate max-w-[300px]">{q.question_text}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {q.course_id}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
