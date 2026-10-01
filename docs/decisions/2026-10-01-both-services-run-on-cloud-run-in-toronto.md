# Both services run on Cloud Run, in Toronto, on the client's own project

Date: 1 October 2026. Decided by the owner's instruction to deploy the web app and
the backend on Google Cloud, and by these facts:

- The client made the owner an owner of their Google Cloud project `ppcway-509313`
  (number 734687676224) and attached billing to it, so the Google spend and the
  Google data now sit in one account that the client controls.
- The audit needs a headless Chromium and keeps working after the page has its
  reply. Vercel functions cannot run the browser at all.
- The landing page promises that data is stored in Canada.

So:

1. Region `northamerica-northeast2` (Toronto) for both services, and for the bucket.
2. `ppcway-api`: 2 vCPU, 2 GB, at most 3 instances, **CPU always allocated**. The
   audit runs after the 202 reply, and Cloud Run's default throttles the CPU at
   that moment, which would leave every free audit unfinished. The cost of that
   choice is instance time, roughly $15 to $30 a month at low use.
3. `ppcway-web`: 1 vCPU, 1 GB, at most 3 instances, default CPU. It only renders.
4. Screenshots are written to the bucket `ppcway-audit-shots`, mounted at
   `/app/data/shots`. A Cloud Run disk is thrown away with the instance, and the
   report shows the screenshots for as long as the report exists.
5. Secrets (the Neon URL, the Maps key, the PageSpeed key) live in Secret Manager
   and reach the service as environment variables. Nothing is baked into an image;
   `web/.dockerignore` keeps `.env` out of the web image.
6. The database stays Neon rather than Cloud SQL. The proof of concept's data is
   there, this repository's migrations only add tables, and moving it is a separate
   decision.
7. The Vercel deployment is left running and untouched, so the two can be compared
   before anything is turned off.

Two things this cost us, both now fixed in the repository:

- `playwright` was a floor (`>=1.49`), so the image installed a newer Playwright
  than the Chromium baked into its base image and every render failed with
  "Executable doesn't exist". It is pinned to the base image's version now.
- Google's front end swallows `/healthz` on Cloud Run: the request never reaches
  the container. The same answer is served at `/v1/healthz`.

What this costs if wrong: if the client later wants the services in their own
organisation or another region, the move is a redeploy with different flags; the
images and the code do not change.
