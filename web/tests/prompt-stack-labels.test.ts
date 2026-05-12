import { describe, expect, test } from "vitest";

import {
  actionLabel,
  kindLabel,
  layerTitleLabel,
  reasonLabel,
  scopeLabel,
} from "@/lib/prompt-stack-labels";

describe("prompt stack labels", () => {
  test("maps known prompt asset labels", () => {
    expect(kindLabel("lorebook_entry")).toBe("世界书");
    expect(kindLabel("character_card")).toBe("角色卡");
    expect(kindLabel("author_note")).toBe("作者注释");
    expect(scopeLabel("project")).toBe("项目");
    expect(scopeLabel("chapter")).toBe("章节");
    expect(reasonLabel("always_on")).toBe("Always-on");
    expect(reasonLabel("keyword")).toBe("关键词");
    expect(layerTitleLabel("Active Lorebook Entries")).toBe("世界书");
    expect(layerTitleLabel("Active Character Cards")).toBe("角色卡");
    expect(layerTitleLabel("Author Notes")).toBe("作者注释");
    expect(actionLabel("new")).toBe("新增");
    expect(actionLabel("update")).toBe("更新");
    expect(actionLabel("disable")).toBe("禁用");
  });

  test("falls back to raw values for unknown backend labels", () => {
    expect(kindLabel("custom_kind")).toBe("custom_kind");
    expect(scopeLabel("custom_scope")).toBe("custom_scope");
    expect(reasonLabel("custom_reason")).toBe("custom_reason");
    expect(layerTitleLabel("Custom Layer")).toBe("Custom Layer");
  });
});
