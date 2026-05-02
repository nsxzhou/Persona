import { describe, expect, test } from "vitest";

import {
  parseOutline,
  replaceVolumeChapters,
  type ParsedChapter,
  type ParsedOutline,
  type ParsedVolume,
} from "@/lib/outline-parser";

describe("parseOutline", () => {
  test("multi-volume format with chapters produces correct tree structure", () => {
    const md = `## 第一卷：黎明之前
> 主题：觉醒与出发 | 字数范围：0-5万字

### 第 1 章：被遗忘的名字
- **核心事件**：主角在废墟中醒来
- **情绪走向**：迷茫 → 恐惧 → 坚定
- **章末钩子**：手臂上的倒计时开始跳动

### 第 2 章：灰色的天空
- **核心事件**：主角逃出废墟
- **情绪走向**：紧张 → 释然
- **章末钩子**：远方传来号角声

## 第二卷：破晓之时
> 主题：成长与挑战 | 字数范围：5-10万字

### 第 3 章：陌生的同伴
- **核心事件**：主角遇到旅伴
- **情绪走向**：警惕 → 信任
- **章末钩子**：旅伴的秘密身份暴露`;

    const result = parseOutline(md);

    expect(result.parseErrors).toEqual([]);
    expect(result.volumes).toHaveLength(2);

    const vol1 = result.volumes[0];
    expect(vol1.title).toBe("第一卷：黎明之前");
    expect(vol1.meta).toBe("主题：觉醒与出发 | 字数范围：0-5万字");
    expect(vol1.bodyMarkdown).toBe("> 主题：觉醒与出发 | 字数范围：0-5万字");
    expect(vol1.chapters).toHaveLength(2);

    expect(vol1.chapters[0].title).toBe("第 1 章：被遗忘的名字");
    expect(vol1.chapters[0].coreEvent).toBe("主角在废墟中醒来");
    expect(vol1.chapters[0].emotionArc).toBe("迷茫 → 恐惧 → 坚定");
    expect(vol1.chapters[0].chapterHook).toBe("手臂上的倒计时开始跳动");

    expect(vol1.chapters[1].title).toBe("第 2 章：灰色的天空");
    expect(vol1.chapters[1].coreEvent).toBe("主角逃出废墟");

    const vol2 = result.volumes[1];
    expect(vol2.title).toBe("第二卷：破晓之时");
    expect(vol2.meta).toBe("主题：成长与挑战 | 字数范围：5-10万字");
    expect(vol2.chapters).toHaveLength(1);
    expect(vol2.chapters[0].title).toBe("第 3 章：陌生的同伴");
  });

  test("short-novel format (acts as volumes with ### chapters) works", () => {
    const md = `### 第 1 章：开端
- **核心事件**：故事开始
- **情绪走向**：平静 → 紧张
- **章末钩子**：悬念出现

### 第 2 章：发展
- **核心事件**：冲突升级
- **情绪走向**：紧张 → 高潮
- **章末钩子**：转折点`;

    const result = parseOutline(md);

    expect(result.parseErrors).toEqual([]);
    // Should produce a single implicit volume with chapters
    expect(result.volumes).toHaveLength(1);
    expect(result.volumes[0].title).toBe("");
    expect(result.volumes[0].meta).toBe("");
    expect(result.volumes[0].bodyMarkdown).toBe("");
    expect(result.volumes[0].chapters).toHaveLength(2);
    expect(result.volumes[0].chapters[0].title).toBe("第 1 章：开端");
    expect(result.volumes[0].chapters[1].title).toBe("第 2 章：发展");
  });

  test("unparseable content returns empty volumes and parseErrors", () => {
    const md = `这是一段没有任何标题格式的文字。
只是普通段落。`;

    const result = parseOutline(md);

    expect(result.volumes).toEqual([]);
    expect(result.parseErrors.length).toBeGreaterThan(0);
  });

  test("empty string returns empty volumes with no errors", () => {
    const result = parseOutline("");

    expect(result.volumes).toEqual([]);
    expect(result.parseErrors).toEqual([]);
  });

  test("chapters with missing fields return empty strings without crash", () => {
    const md = `## 第一卷：测试卷

### 第 1 章：缺失字段章节
- **核心事件**：有核心事件
- 这行不是标准字段`;

    const result = parseOutline(md);

    expect(result.volumes).toHaveLength(1);
    const ch = result.volumes[0].chapters[0];
    expect(ch.title).toBe("第 1 章：缺失字段章节");
    expect(ch.coreEvent).toBe("有核心事件");
    expect(ch.emotionArc).toBe("");
    expect(ch.chapterHook).toBe("");
  });

  test("rawMarkdown is preserved per chapter", () => {
    const md = `## 第一卷：原文测试

### 第 1 章：保留原文
- **核心事件**：测试原文保留
- **情绪走向**：平静
- **章末钩子**：结束`;

    const result = parseOutline(md);

    const raw = result.volumes[0].chapters[0].rawMarkdown;
    expect(raw).toContain("### 第 1 章：保留原文");
    expect(raw).toContain("**核心事件**：测试原文保留");
    expect(raw).toContain("**情绪走向**：平静");
    expect(raw).toContain("**章末钩子**：结束");
  });

  test("volume without meta blockquote has empty meta", () => {
    const md = `## 第一卷：无元数据

### 第 1 章：测试
- **核心事件**：事件`;

    const result = parseOutline(md);

    expect(result.volumes[0].meta).toBe("");
    expect(result.volumes[0].chapters[0].coreEvent).toBe("事件");
  });

  test("fields with colon variant (English colon) are parsed", () => {
    const md = `## 第一卷：冒号测试

### 第 1 章：英文冒号
- **核心事件**: 使用英文冒号
- **情绪走向**: 测试
- **章末钩子**: 完成`;

    const result = parseOutline(md);

    const ch = result.volumes[0].chapters[0];
    expect(ch.coreEvent).toBe("使用英文冒号");
    expect(ch.emotionArc).toBe("测试");
    expect(ch.chapterHook).toBe("完成");
  });

  test("legacy 章节末推动点 field is parsed as chapterHook", () => {
    const md = `## 第一卷：旧格式

### 第 1 章：兼容测试
- **核心事件**：旧格式事件
- **情绪走向**：平静 → 紧张
- **章节末推动点**：旧字段兼容成功`;

    const result = parseOutline(md);

    expect(result.volumes).toHaveLength(1);
    expect(result.volumes[0].chapters[0].chapterHook).toBe("旧字段兼容成功");
  });

  test("volume planning markdown ignores top-level title and volume-level ### sections", () => {
    const md = `# 《最后三个月》全书分卷规划

## 第一卷：撕掉标签（第1-8章）

> 主题：当系统抛弃你之前，你先抛弃系统 | 当前压力：诊断书+母亲期待

### 主驱动轴
力量与权力的初次解放。

### 本卷核心兑现物
**规则的第一次被打破**：庄晏当着班主任的面说“我自愿堕落”。

### 第 1 章：诊断书
- **核心事件**：庄晏拿到诊断书
- **情绪走向**：麻木 → 压抑
- **章末钩子**：他决定退学

## 全篇闭环验证

| 要素 | 验证结果 |
|------|---------|
| 开局压制 | 诊断书 |`;

    const result = parseOutline(md);

    expect(result.parseErrors).toEqual([]);
    expect(result.volumes).toHaveLength(1);
    expect(result.volumes[0].title).toBe("第一卷：撕掉标签（第1-8章）");
    expect(result.volumes[0].bodyMarkdown).toContain("### 主驱动轴");
    expect(result.volumes[0].bodyMarkdown).toContain("### 本卷核心兑现物");
    expect(result.volumes[0].chapters).toHaveLength(1);
    expect(result.volumes[0].chapters[0].title).toBe("第 1 章：诊断书");
  });

  test("fallback parses table-based volume rhythm into real chapter tree", () => {
    const md = `## 第一卷：撕掉标签的第一天（第1-8章）

> 主题：系统抛弃你之前，你先抛弃系统 | 当前压力：三个月倒计时启动

### 本卷核心驱动轴
从“被系统控制的优等生”到“主动打破规则的叛逆者”。

### 节奏设计
| 环节 | 章号 | 内容 | 追读驱动 |
|------|------|------|---------|
| 压制 | 第1章 | 诊断书+办公室对话 | 他怎么办？ |
| 压制 | 第2章 | 围墙相遇，苏晚晴出现 | 这个女孩是什么人？ |
| 反击 | 第3章 | 教务处谈话——翻窗出去 | 他真的敢退学吗？ |

### 章末压力设计
- 第1章：母亲站在办公室门口等他出来，他只能笑着说“没事”
- 第2章：苏晚晴翻下围墙，回头说“听说你想学坏？”

## 全篇爽点密度表

| 阶段 | 章数 |
|------|------|
| 第一卷 | 8章 |`;

    const result = parseOutline(md);

    expect(result.parseErrors).toEqual([]);
    expect(result.volumes).toHaveLength(1);
    expect(result.volumes[0].title).toBe("第一卷：撕掉标签的第一天（第1-8章）");
    expect(result.volumes[0].bodyMarkdown).toContain("### 本卷核心驱动轴");
    expect(result.volumes[0].bodyMarkdown).not.toContain("### 节奏设计");
    expect(result.volumes[0].chapters.map((chapter) => chapter.title)).toEqual([
      "第1章：诊断书+办公室对话",
      "第2章：围墙相遇，苏晚晴出现",
      "第3章：教务处谈话——翻窗出去",
    ]);
    expect(result.volumes[0].chapters[0].coreEvent).toBe("诊断书+办公室对话");
    expect(result.volumes[0].chapters[0].chapterHook).toBe("母亲站在办公室门口等他出来，他只能笑着说“没事”");
    expect(result.volumes[0].chapters[2].chapterHook).toBe("他真的敢退学吗？");
  });

  test("fallback expands ranged list chapters into single chapter nodes", () => {
    const md = `## 第二卷：偷来的自由（第9-20章）

> 主题：在追捕中学会呼吸

### 主要节奏
- 第9-11章：校内追捕升级，庄晏利用陈勉的信息网络不断预判林景行的行动
- 第12章：【核心爽点】周远派人来书店找茬

### 章末压力起点
- 第12章结尾：周远走前看他的眼神——不是恨，是怕`;

    const result = parseOutline(md);

    expect(result.volumes).toHaveLength(1);
    expect(result.volumes[0].chapters.map((chapter) => chapter.title)).toEqual([
      "第9章：校内追捕升级，庄晏利用陈勉的信息网络不断预判林景行的行动",
      "第10章：校内追捕升级，庄晏利用陈勉的信息网络不断预判林景行的行动",
      "第11章：校内追捕升级，庄晏利用陈勉的信息网络不断预判林景行的行动",
      "第12章：【核心爽点】周远派人来书店找茬",
    ]);
    expect(result.volumes[0].chapters[3].chapterHook).toBe("周远走前看他的眼神——不是恨，是怕");
  });

  test("replaceVolumeChapters preserves volume body markdown", () => {
    const md = `# 书名

## 第一卷：撕掉标签
> 主题：压力

### 主驱动轴
力量释放。

### 第 1 章：旧章
- **核心事件**：旧事件

## 第二卷：偷来的自由
> 主题：逃亡`;

    const result = replaceVolumeChapters(
      md,
      0,
      "### 第 1 章：新章\n- **核心事件**：新事件",
    );

    expect(result).toContain("# 书名");
    expect(result).toContain("### 主驱动轴\n力量释放。");
    expect(result).toContain("### 第 1 章：新章");
    expect(result).not.toContain("### 第 1 章：旧章");
    expect(result).toContain("## 第二卷：偷来的自由");
  });
});
