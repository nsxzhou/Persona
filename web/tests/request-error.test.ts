import { expect, test } from "vitest";

import { parseApiErrorDetail } from "@/lib/request-error";

test("parseApiErrorDetail returns JSON detail when present", () => {
  expect(parseApiErrorDetail('{"detail":"错误详情"}', "Fallback")).toBe("错误详情");
});

test("parseApiErrorDetail falls back to plain text or status text", () => {
  expect(parseApiErrorDetail("Bad Gateway", "Fallback")).toBe("Bad Gateway");
  expect(parseApiErrorDetail("", "Fallback")).toBe("Fallback");
});
