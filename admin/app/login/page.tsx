"use client";

import { useRouter, useSearchParams } from "next/navigation";
import type { FormEvent } from "react";
import { Suspense, startTransition, useState } from "react";

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [adminUserId, setAdminUserId] = useState("101");
  const [email, setEmail] = useState("admin@example.com");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const nextPath = searchParams.get("next") || "/";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);

    document.cookie = [
      `admin_session=${encodeURIComponent(adminUserId)}`,
      "path=/",
      "SameSite=Lax",
    ].join("; ");

    startTransition(() => {
      router.push(nextPath);
      router.refresh();
    });
  }

  return (
    <main className="login-screen">
      <section className="login-hero">
        <p className="eyebrow">Staff access</p>
        <h1>Adarkwa Study Bot Admin</h1>
        <p className="lead">
          A controlled operations desk for analytics, question corrections, and catalog
          governance.
        </p>
        <div className="login-note">
          <span>Subdomain</span>
          <strong>admin.adarkwa.study</strong>
        </div>
      </section>

      <section className="login-card">
        <h2>Sign in</h2>
        <p>Use a staff identity to continue into the operations console.</p>
        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Staff user id
            <input
              name="adminUserId"
              inputMode="numeric"
              value={adminUserId}
              onChange={(event) => setAdminUserId(event.target.value)}
            />
          </label>
          <label>
            Email
            <input
              name="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Entering..." : "Enter admin"}
          </button>
        </form>
        <p className="login-footnote">
          This scaffold stores a demo session cookie until the API-backed auth flow is wired.
        </p>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="login-screen" />}>
      <LoginPageContent />
    </Suspense>
  );
}
