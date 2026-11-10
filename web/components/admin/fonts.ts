import localFont from "next/font/local";

/*
  The console's two faces, loaded only where the console is drawn.

  Public Sans for every word: a plain, sturdy grotesk built for screens people
  work in all day. IBM Plex Mono for every figure, so a column of counts,
  times and Google Ads ids stacks digit under digit. One job each; never a
  third.

  Kept apart from the root layout so the merchant app and the public site do
  not download a typeface they never use.
*/
// From files in `app/fonts/`, not Google Fonts, so a build never downloads
// them -- see the note in `app/layout.tsx`.
export const adSans = localFont({
  src: "../../app/fonts/public-sans-latin-wght-normal.woff2",
  variable: "--font-ad-sans",
  weight: "100 900",
  display: "swap",
});

export const adMono = localFont({
  src: [
    {
      path: "../../app/fonts/ibm-plex-mono-latin-400-normal.woff2",
      weight: "400",
      style: "normal",
    },
    {
      path: "../../app/fonts/ibm-plex-mono-latin-500-normal.woff2",
      weight: "500",
      style: "normal",
    },
  ],
  variable: "--font-ad-mono",
  display: "swap",
});
