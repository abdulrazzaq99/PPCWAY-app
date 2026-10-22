import type { Metadata } from "next";
import { Suspense } from "react";
import { NotOpenYet } from "@/components/auth/not-open-yet";
import { SignupForm } from "@/components/auth/signup-form";
import { isOpen } from "@/lib/open";

export const metadata: Metadata = { title: "Create your account · PPCWay" };

/*
  Whether anybody may make an account is the backend's answer, asked here on the
  server so nobody is shown a form that will be refused. Signing in is left
  alone: the people already inside, and the reviewers Google sends us, arrive
  through /login and must not meet a closed door.
*/
export default async function SignupPage() {
  if (!(await isOpen())) return <NotOpenYet />;
  return (
    <Suspense>
      <SignupForm />
    </Suspense>
  );
}
