import { IBM_Plex_Mono, Public_Sans } from "next/font/google";

/*
  The console's two faces, loaded only where the console is drawn.

  Public Sans for every word: a plain, sturdy grotesk built for screens people
  work in all day. IBM Plex Mono for every figure, so a column of counts,
  times and Google Ads ids stacks digit under digit. One job each; never a
  third.

  Kept apart from the root layout so the merchant app and the public site do
  not download a typeface they never use.
*/
export const adSans = Public_Sans({
  variable: "--font-ad-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const adMono = IBM_Plex_Mono({
  variable: "--font-ad-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});
