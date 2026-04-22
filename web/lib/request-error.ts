interface FastApiValidationItem {
  loc?: (string | number)[];
  msg: string;
  type?: string;
}

export class RequestError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "RequestError";
    this.status = status;
    this.detail = detail;
  }
}

export function parseApiErrorDetail(text: string, fallback: string): string {
  if (!text) {
    return fallback;
  }

  try {
    const data = JSON.parse(text) as Record<string, unknown>;

    // Handle standard FastAPI error or generic detail string
    if (data.detail !== undefined) {
      if (typeof data.detail === "string" && data.detail.trim()) {
        return data.detail;
      }

      // Handle FastAPI 422 Validation Error array
      if (Array.isArray(data.detail)) {
        const messages = (data.detail as FastApiValidationItem[]).map((err) => {
          const loc = Array.isArray(err.loc) ? err.loc.join(".") : "";
          return loc ? `${loc}: ${err.msg}` : err.msg;
        });
        if (messages.length > 0) {
          return messages.join(", ");
        }
      }
    }

    // Fallback to generic message or error fields
    if (typeof data.message === "string" && data.message.trim()) {
      return data.message;
    }
    if (typeof data.error === "string" && data.error.trim()) {
      return data.error;
    }
  } catch {
    return text;
  }

  return text || fallback;
}
