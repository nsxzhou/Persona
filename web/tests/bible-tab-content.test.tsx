import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, test } from "vitest";

import { BibleTabContent } from "@/components/bible-tab-content";

function WorldBuildingTemplateHarness() {
  const [value, setValue] = useState("");

  return (
    <BibleTabContent
      fieldKey="world_building"
      title="世界观设定"
      value={value}
      onChange={setValue}
      aiEnabled={false}
      prerequisiteWarning={null}
      isGenerating={false}
      onGenerate={() => undefined}
      onStopGenerate={() => undefined}
    />
  );
}

describe("BibleTabContent", () => {
  test("inserts the de-templated world building scaffold from the empty state", () => {
    render(<WorldBuildingTemplateHarness />);

    fireEvent.click(screen.getByRole("button", { name: "使用模板" }));

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;

    expect(textarea.value).toContain("## 核心时代与生活秩序");
    expect(textarea.value).toContain("## 权力结构与身份壁垒");
    expect(textarea.value).toContain("## 主角当前处境与约束");
    expect(textarea.value).toContain("## 当前局势与旧事阴影");
    expect(textarea.value).toContain("## 后续可能扩展的空间（如有）");
    expect(textarea.value).not.toContain("## 规则体系");
    expect(textarea.value).not.toContain("## 历史大事件");
  });
});
