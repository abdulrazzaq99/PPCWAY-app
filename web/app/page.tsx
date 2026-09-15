import { redirect } from "next/navigation";

/* The overview lives here once the dashboard is built. Until then, the door is sign-in. */
export default function Home() {
  redirect("/login");
}
