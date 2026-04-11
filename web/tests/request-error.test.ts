import { expect, test } from "vitest";

import { parseApiErrorDetail } from "@/lib/request-error";

test("parseApiErrorDetail returns JSON detail when present", () => {
  expect(parseApiErrorDetail('{"detail":"错误详情"}', "Fallback")).toBe("错误详情");
});

test("parseApiErrorDetail falls back to plain text or status text", () => {
  expect(parseApiErrorDetail("Bad Gateway", "Fallback")).toBe("Bad Gateway");
  expect(parseApiErrorDetail("", "Fallback")).toBe("Fallback");
});

test("parseApiErrorDetail parses FastAPI 422 validation error array", () => {
  const errorJson = JSON.stringify({
    detail: [
      { loc: ["body", "username"], msg: "field required", type: "value_error.missing" }
    ]
  });
  expect(parseApiErrorDetail(errorJson, "Fallback")).toBe("body.username: field required");
});

test("parseApiErrorDetail parses message or error fields", () => {
  expect(parseApiErrorDetail('{"message":"custom error"}', "Fallback")).toBe("custom error");
  expect(parseApiErrorDetail('{"error":"another error"}', "Fallback")).toBe("another error");
});
