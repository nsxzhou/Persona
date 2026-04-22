import { describe, expect, test, vi } from "vitest";
import { RequestError } from "@/lib/request-error";

describe("getServerCurrentUser", () => {
  test("returns null for typed 401 errors only", async () => {
    vi.resetModules();
    vi.doMock("next/headers", () => ({
      cookies: async () => ({ toString: () => "" }),
    }));
    vi.doMock("@/lib/api", () => ({
      API_BASE_URL: "http://localhost:8000",
    }));
    vi.doMock("@/lib/api/transport", () => ({
      createJsonRequester: () => ({ raw: vi.fn() }),
    }));
    vi.doMock("@/lib/api-client", () => ({
      createApiClient: () => ({
        getCurrentUser: vi.fn().mockRejectedValue(new RequestError(401, "Unauthorized")),
      }),
    }));

    const { getServerCurrentUser } = await import("@/lib/server-api");
    await expect(getServerCurrentUser()).resolves.toBeNull();
  });

  test("rethrows non-401 typed errors", async () => {
    vi.resetModules();
    vi.doMock("next/headers", () => ({
      cookies: async () => ({ toString: () => "" }),
    }));
    vi.doMock("@/lib/api", () => ({
      API_BASE_URL: "http://localhost:8000",
    }));
    vi.doMock("@/lib/api/transport", () => ({
      createJsonRequester: () => ({ raw: vi.fn() }),
    }));
    vi.doMock("@/lib/api-client", () => ({
      createApiClient: () => ({
        getCurrentUser: vi.fn().mockRejectedValue(new RequestError(500, "boom")),
      }),
    }));

    const { getServerCurrentUser } = await import("@/lib/server-api");
    await expect(getServerCurrentUser()).rejects.toThrow("boom");
  });
});
