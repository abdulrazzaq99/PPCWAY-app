import { AdminSpec, audit } from "@/components/app/admin-views";

export default function Page() {
  return <AdminSpec spec={audit} />;
}
