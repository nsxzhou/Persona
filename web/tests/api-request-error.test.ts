import { expect, test, vi } from "vitest";

import { api } from "@/lib/api";

test("api request throws plain-text error details when response is not JSON", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: vi.fn().mockRejectedValue(new Error("not json")),
      text: vi.fn().mockResolvedValue("Bad Gateway"),
    })
  );

  await expect(api.getProviderConfigs()).rejects.toThrow("Bad Gateway");
});

