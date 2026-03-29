"use client";

import { useState } from "react";
import { AdminShell } from "@/components/admin-shell";
import { MillerColumns } from "@/components/catalog/miller-columns";

export default function CatalogPage() {
  return (
    <AdminShell>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Catalog</h2>
          <p className="text-sm text-muted-foreground">
            Navigate the academic structure: Faculty → Program → Level → Semester → Course.
          </p>
        </div>
        <MillerColumns />
      </div>
    </AdminShell>
  );
}
