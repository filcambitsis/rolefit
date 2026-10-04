import { createClient } from "@supabase/supabase-js";
const base = process.env.NEXT_PUBLIC_API_URL || "";
export const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true" || !base;
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
export const supabase =
  supabaseUrl && anonKey ? createClient(supabaseUrl, anonKey) : null;
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const session = supabase
    ? (await supabase.auth.getSession()).data.session
    : null;
  const headers: Record<string, string> = {};
  if (session) headers.Authorization = `Bearer ${session.access_token}`;
  if (options.body && !(options.body instanceof FormData))
    headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${base}${path}`, {
      ...options,
      headers: { ...headers, ...options.headers },
    });
  } catch {
    throw new Error(
      "Could not reach RoleFit. Check that the server is running and try again.",
    );
  }
  if (!res.ok) {
    const body = await res
      .json()
      .catch(() => ({ detail: "Could not reach RoleFit. Please try again." }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Please check the information you entered.",
    );
  }
  return res.status === 204 ? (undefined as T) : res.json();
}
