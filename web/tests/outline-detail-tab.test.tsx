import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { OutlineDetailTab } from "@/components/outline-detail-tab";

const apiMock = vi.hoisted(() => ({
  runVolumeWorkflow: vi.fn(),
  runVolumeChaptersWorkflow: vi.fn(),
  updateProject: vi.fn(),
  updateProjectBible: vi.fn(),
}));

const toastMock = vi.hoisted(() => ({
  error: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: toastMock,
}));

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

function createSseResponse(markdown: string) {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify(markdown)}\n\n`));
      controller.close();
    },
  });
  return new Response(stream);
}

describe("OutlineDetailTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders unified toolbar modes and compact volume overview", () => {
    render(
      <OutlineDetailTab
        value={`## 第一卷 反派开局
> 主打反转与误导

### 主驱动轴
反派身份的误导与自救

### 第1章 反派开局，短命名单
- **核心事件**：开局认命

### 第2章 纨绔是假装，天香楼才是入口
- **核心事件**：天香楼试探`}
        onChange={vi.fn()}
        projectId="project-1"
        outlineMaster="已存在总纲"
        {...({
          chapters: [
            {
              id: "chapter-1",
              project_id: "project-1",
              volume_index: 0,
              chapter_index: 0,
              title: "第1章 反派开局，短命名单",
              content: "正文",
              word_count: 2,
              created_at: "2026-04-10T00:00:00Z",
              updated_at: "2026-04-10T00:00:00Z",
            },
          ],
        } as Record<string, unknown>)}
      />,
    );

    expect(screen.getByRole("button", { name: "编辑" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "预览" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "AI 生成" })).toBeInTheDocument();
    expect(screen.getByText("第一卷 反派开局")).toBeInTheDocument();
    expect(screen.getByText("已完成 1/2 章")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "主驱动轴" })).not.toBeInTheDocument();
    expect(screen.queryByText("第1章 反派开局，短命名单")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看章节" }));

    const chapterLink = screen.getByRole("link", { name: "第1章 反派开局，短命名单" });
    expect(chapterLink).toHaveAttribute(
      "href",
      "/projects/project-1/editor?volumeIndex=0&chapterIndex=0&intent=navigate",
    );

    const generateLink = screen.getByRole("link", { name: "AI 生成 第1章 反派开局，短命名单" });
    expect(generateLink).toHaveAttribute(
      "href",
      "/projects/project-1/editor?volumeIndex=0&chapterIndex=0&intent=generate_beats",
    );
  });

  test("shows generate button for a volume without chapters and confirm before regenerating an existing volume", () => {
    render(
      <OutlineDetailTab
        value={`## 第一幕：高危开局与关系占位
> 主题：先活下来，把必死反派改造成可操盘变量 | 字数范围：0-4万字

## 第二幕：洗白不是认怂，结盟就是换资源
> 主题：从单点自救转向结构经营，把名声、关系与组织力一起做出来 | 字数范围：4-8万字

### 第1章 纨绔是假装，天香楼才是入口
- **核心事件**：天香楼试探`}
        onChange={vi.fn()}
        projectId="project-2"
        outlineMaster="已存在总纲"
        chapters={[]}
      />,
    );

    expect(screen.getByRole("button", { name: "生成本卷章节细纲" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重新生成章节细纲" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重新生成章节细纲" }));
    expect(screen.getByText("重新生成第 2 卷章节细纲")).toBeInTheDocument();
    expect(
      screen.getByText("当前卷下已生成的章节细纲将被覆盖。你可以填写意见指导生成方向（可选）。"),
    ).toBeInTheDocument();
  });

  test("blocks persisting generated chapter details without standard chapter headings", async () => {
    const onChange = vi.fn();
    const original = `## 第一卷：测试
> 主题：测试`;
    apiMock.runVolumeChaptersWorkflow.mockResolvedValue(
      createSseResponse(`### 节奏设计
| 章号 | 内容 |
|------|------|
| 第1章 | 错误表格 |`),
    );

    render(
      <OutlineDetailTab
        value={original}
        onChange={onChange}
        projectId="project-3"
        outlineMaster="已存在总纲"
        chapters={[]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "生成本卷章节细纲" }));

    await waitFor(() => {
      expect(toastMock.error).toHaveBeenCalledWith(
        "生成结果未包含标准章节标题（### 第 N 章：章名），已阻止写入。请重试或调整意见。",
      );
    });
    expect(apiMock.updateProjectBible).not.toHaveBeenCalled();
    expect(onChange).toHaveBeenLastCalledWith(original);
  });
});
