"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
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
import { MOCK_STAFF, MOCK_QUESTIONS, MOCK_CATALOG } from "@/lib/mock-data";

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

  // Flatten courses from catalog for search
  const courses: { code: string; name: string }[] = [];
  function extractCourses(entries: typeof MOCK_CATALOG) {
    for (const entry of entries) {
      if (!entry.children || entry.children.length === 0) {
        courses.push({ code: entry.code, name: entry.name });
      } else {
        extractCourses(entry.children);
      }
    }
  }
  extractCourses(MOCK_CATALOG);

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
            {MOCK_STAFF.map((staff) => (
              <CommandItem
                key={staff.id}
                onSelect={() => runCommand(() => router.push("/staff"))}
              >
                <Users className="mr-2 size-4" />
                <span>{staff.display_name}</span>
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
            {MOCK_QUESTIONS.slice(0, 5).map((q) => (
              <CommandItem
                key={q.id}
                onSelect={() => runCommand(() => router.push("/questions"))}
              >
                <FileQuestion className="mr-2 size-4" />
                <span className="truncate max-w-[300px]">{q.question_text}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {q.course_code}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
