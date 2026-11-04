/*
  What somebody who is not staff sees at /admin. A plain sentence, not a 403
  screen: the likeliest reader is a merchant who followed a link, and telling
  them the page does not exist would be a lie while telling them they are
  forbidden sounds like an accusation.
*/
export function NotForYou({ trouble }: { trouble?: string }) {
  return (
    <main className="mx-auto max-w-[560px] px-4 py-24">
      <h1 className="text-pw-ink text-[22px] leading-[28px] font-semibold">
        This part of PPCWay is for our own staff
      </h1>
      <p className="text-pw-ink-700 mt-3 text-[15px] leading-[22px]">
        {trouble ||
          "There is nothing here for you to do. Your own dashboard has everything about your account."}
      </p>
      <a
        href="/home"
        className="text-pw-blue mt-5 inline-block text-[15px] leading-[22px] font-medium underline underline-offset-2"
      >
        Go to your dashboard
      </a>
    </main>
  );
}
