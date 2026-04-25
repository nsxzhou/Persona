import { describe, expect, test } from "vitest";

import { LENGTH_PRESETS } from "@/lib/length-presets";

describe("LENGTH_PRESETS", () => {
  test("uses the updated soft length hint copy for each preset", () => {
    expect(LENGTH_PRESETS.short.description).toBe("预计体量偏短，几万或者十几万字");
    expect(LENGTH_PRESETS.medium.description).toBe("预计体量中等，几十万字");
    expect(LENGTH_PRESETS.long.description).toBe("预计体量偏长，百万字");
  });
});
