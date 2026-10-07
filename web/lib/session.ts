/*
  The session cookie. It holds the token the backend issued; it is httpOnly, so
  only the server ever reads it, and the browser just carries it.
*/
export const SESSION_COOKIE = "ppcway_session";
export const SESSION_DAYS = 30;

export const cookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 24 * SESSION_DAYS,
};
