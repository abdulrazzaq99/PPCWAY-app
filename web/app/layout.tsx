import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

/*
  The typefaces, from files in `app/fonts/` rather than from Google Fonts.

  `next/font/google` downloads each face while the site is built, and on 6 and
  10 November that download failed inside Cloud Build ("Can't resolve
  '@vercel/turbopack-next/internal/font/google/font'"), taking the whole deploy
  down with it though the code was fine. The files are now part of the repo --
  each under the SIL Open Font License, which allows that, with its licence
  beside it -- so a build never reaches out for them. Latin only, as before,
  and the variable cut of each face, which covers every weight in one file.

  The signed-in app uses Inter, from Version 2. The public pages use the
  client's own website faces: Outfit for headings, DM Sans for everything else.
*/
const inter = localFont({
  src: "./fonts/inter-latin-wght-normal.woff2",
  variable: "--font-inter",
  weight: "100 900",
  display: "swap",
});

const outfit = localFont({
  src: "./fonts/outfit-latin-wght-normal.woff2",
  variable: "--font-outfit",
  weight: "100 900",
  display: "swap",
});

const dmSans = localFont({
  src: "./fonts/dm-sans-latin-wght-normal.woff2",
  variable: "--font-dm-sans",
  weight: "100 1000",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PPCWay",
  description:
    "Google Ads for small businesses, run in plain words. You approve, we explain, every change can be undone.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${outfit.variable} ${dmSans.variable} h-full`}>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
