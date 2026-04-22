import { parseApiErrorDetail, RequestError } from "@/lib/request-error";

type RequesterOptions = {
  baseUrl: string;
  defaultInit?: RequestInit;
};

function buildUrl(baseUrl: string, path: string) {
  return `${baseUrl}${path}`;
}

export function createJsonRequester({ baseUrl, defaultInit }: RequesterOptions) {
  const buildRequestArgs = (path: string, init?: RequestInit) => {
    const headers = new Headers(defaultInit?.headers ?? undefined);
    if (init?.headers) {
      for (const [key, value] of Object.entries(Object.fromEntries(new Headers(init.headers).entries()))) {
        if (value === "undefined") {
          headers.delete(key);
          continue;
        }
        headers.set(key, value);
      }
    }
    if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    return {
      url: buildUrl(baseUrl, path),
      options: {
        ...defaultInit,
        ...init,
        headers,
      },
    };
  };

  const request = async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const { url, options } = buildRequestArgs(path, init);
    const response = await fetch(url, options);

    if (!response.ok) {
      const text = await response.text();
      throw new RequestError(
        response.status,
        parseApiErrorDetail(text, response.statusText || "请求失败"),
      );
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

  const requestRaw = async function requestRaw(path: string, init?: RequestInit): Promise<Response> {
    const { url, options } = buildRequestArgs(path, init);
    const response = await fetch(url, options);
    
    if (!response.ok) {
      const text = await response.text();
      throw new RequestError(
        response.status,
        parseApiErrorDetail(text, response.statusText || "请求失败"),
      );
    }
    
    return response;
  };

  request.raw = requestRaw;

  return request;
}
