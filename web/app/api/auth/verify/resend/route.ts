import { pass } from "@/lib/pw-proxy";

/* Another confirmation link, for somebody who lost the first. */
export async function POST() {
  return pass("/v1/auth/verify/resend", { method: "POST" });
}
