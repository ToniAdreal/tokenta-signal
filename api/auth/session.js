// Tokenta Signal auth: legacy endpoint. It used to adopt sessions that
// arrived as Supabase tokens in an email-link URL fragment. The self-hosted
// backend sets cookies directly in its OAuth callbacks and code verify
// flow, so nothing posts here any more. Kept as a stub so stale cached
// pages fail soft instead of hitting a 404.
import { cors } from "./_lib.js";

export default async function handler(req, res) {
  cors(req, res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  return res.status(410).json({ error: "gone" });
}
