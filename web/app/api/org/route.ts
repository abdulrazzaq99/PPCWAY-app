import { pass } from "@/lib/pw-proxy";

/* The business, who is in it, and what you may do. */
export async function GET() {
  return pass("/v1/org");
}
