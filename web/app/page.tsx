import type { Metadata } from "next";
import { Landing } from "@/components/landing/landing";

export const metadata: Metadata = {
  title: "PPCWay: Google Ads that look after themselves",
  description:
    "We write the campaign, watch it every day, and explain every change in plain words. Start with a free check of your website.",
};

export default function Home() {
  return <Landing />;
}
