/*
  The session cookie. It holds the token the backend issued; it is httpOnly, so
  only the server ever reads it, and the browser just carries it.
*/
export const SESSION_COOKIE = "ppcway_session";
/*
  Audits run in this browser before anybody signed in. Somebody runs the free
  audit, likes what it says and makes an account: this is how the report they were
  reading follows them in, rather than a new account that looks empty.
*/
export const RAN_HERE_COOKIE = "ppcway_ran_here";
export const RAN_HERE_KEEP = 10;
export const SESSION_DAYS = 30;

export const cookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * SESSION_DAYS,
};
