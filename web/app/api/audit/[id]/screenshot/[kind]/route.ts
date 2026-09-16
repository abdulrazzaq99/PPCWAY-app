const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string; kind: string }> },
) {
  const { id, kind } = await params;
  try {
    const res = await fetch(
      `${BACKEND}/v1/audits/${encodeURIComponent(id)}/screenshot/${encodeURIComponent(kind)}`,
      { cache: "no-store" },
    );
    if (!res.ok) return new Response(null, { status: res.status });
    return new Response(res.body, {
      status: 200,
      headers: { "content-type": "image/jpeg", "cache-control": "public, max-age=86400" },
    });
  } catch {
    return new Response(null, { status: 503 });
  }
}
