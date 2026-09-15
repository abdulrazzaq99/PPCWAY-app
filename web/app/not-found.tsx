import { LinkButton } from "@/components/ui/button";
import { ProblemPage, SearchGlyph } from "@/components/auth/problem-page";

export default function NotFound() {
  return (
    <ProblemPage
      tone="brand"
      icon={<SearchGlyph />}
      code="404 · Page not found"
      headline="We can't find that page."
      body="Your campaigns are running as normal. The link you followed may be old, or typed slightly wrong. Head back to your overview, or search for what you were after."
      actions={
        <>
          <LinkButton href="/">Back to overview</LinkButton>
          <LinkButton href="/search" variant="secondary">
            Search PPCWay
          </LinkButton>
        </>
      }
      footer="Nothing on this page touches your ads."
    />
  );
}
