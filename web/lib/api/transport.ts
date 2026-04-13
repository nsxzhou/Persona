import { parseApiErrorDetail } from "@/lib/request-error";

type RequesterOptions = {
  baseUrl: string;
  defaultInit?: RequestInit;
};

function buildUrl(baseUrl: string, path: string) {
  return `${baseUrl}${path}`;
}

export function createJsonRequester({ baseUrl, defaultInit }: RequesterOptions) {
  return async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers = new Headers(defaultInit?.headers ?? undefined);
    for (const [key, value] of new Headers(init?.headers ?? undefined).entries()) {
      headers.set(key, value);
    }
    if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(buildUrl(baseUrl, path), {
      ...defaultInit,
      ...init,
      headers,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(parseApiErrorDetail(text, response.statusText || "请求失败"));
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("text/plain")) {
      return (await response.text()) as T;
    }

    return response.json() as Promise<T>;
  };
}
