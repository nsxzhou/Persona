export function parseApiErrorDetail(text: string, fallback: string): string {
  if (!text) {
    return fallback;
  }

  try {
    const data = JSON.parse(text) as { detail?: string };
    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
  } catch {
    return text;
  }

  return text || fallback;
}
