import type { components } from "@/lib/api/generated/openapi";
import { formSchema } from "@/lib/validations/style-lab";

type AnalysisReportMarkdownContract = components["schemas"]["AnalysisReportMarkdown"];
type StyleSummaryMarkdownContract = components["schemas"]["StyleSummaryMarkdown"];
type PromptPackMarkdownContract = components["schemas"]["PromptPackMarkdown"];

test("markdown contracts are plain strings", () => {
  const report: AnalysisReportMarkdownContract = "# 执行摘要\n整体文风冷峻。\n";
  const summary: StyleSummaryMarkdownContract = "# 风格名称\n冷白风\n";
  const promptPack: PromptPackMarkdownContract = "# System Prompt\n以冷峻中文小说文风进行创作。\n";

  expect(typeof report).toBe("string");
  expect(typeof summary).toBe("string");
  expect(typeof promptPack).toBe("string");
});

test("style lab form schema accepts markdown fields", () => {
  const values = {
    styleName: "冷白风",
    styleSummaryMarkdown: "# 风格名称\n冷白风\n",
    promptPackMarkdown: "# System Prompt\n以冷峻中文小说文风进行创作。\n",
  };

  expect(formSchema.parse(values)).toEqual(values);
});
