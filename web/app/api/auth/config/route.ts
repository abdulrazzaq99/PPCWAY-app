import { NextResponse } from "next/server";

/*
  The sign-in button's client id, handed to the browser at run time rather than
  baked in. Next inlines NEXT_PUBLIC_ values when the image is built, which would
  mean rebuilding to change it; this way it is an ordinary setting on the service.
  The id is public by construction: it travels in every sign-in request.
*/
export async function GET() {
  return NextResponse.json({ clientId: process.env.GOOGLE_SIGNIN_CLIENT_ID ?? "" });
}
