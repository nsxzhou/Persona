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

function DescriptionTemplateHarness() {
  const [value, setValue] = useState("");

  return (
    <BibleTabContent
      fieldKey="description"
      title="简介"
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
  test("inserts a project description scaffold instead of inspiration notes", () => {
    render(<DescriptionTemplateHarness />);

    fireEvent.click(screen.getByRole("button", { name: "使用模板" }));

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;

    expect(textarea.value).toContain("## 故事定位");
    expect(textarea.value).toContain("## 开篇切口");
    expect(textarea.value).toContain("## 主线冲突");
    expect(textarea.value).toContain("## 核心看点");
    expect(textarea.value).toContain("## 简介正文");
    expect(textarea.value).not.toContain("## 主题");
    expect(textarea.value).not.toContain("## 目标读者");
    expect(textarea.value).not.toContain("一句话描述核心创意");
  });

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
