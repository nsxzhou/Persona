import type { components } from "@/lib/api/generated/openapi";
import { formSchema } from "@/lib/validations/style-lab";

type AnalysisReportMarkdownContract = components["schemas"]["AnalysisReportMarkdown"];
type VoiceProfileMarkdownContract = components["schemas"]["VoiceProfileMarkdown"];

test("markdown contracts are plain strings", () => {
  const report: AnalysisReportMarkdownContract = "# 执行摘要\n整体文风冷峻。\n";
  const voiceProfile: VoiceProfileMarkdownContract =
    "# Voice Profile\n## 3.1 口头禅与常用表达\n- 短句推进\n";

  expect(typeof report).toBe("string");
  expect(typeof voiceProfile).toBe("string");
});

test("style lab form schema accepts markdown fields", () => {
  const values = {
    styleName: "冷白风",
    voiceProfileMarkdown: "# Voice Profile\n## 3.1 口头禅与常用表达\n- 短句推进\n",
  };

  expect(formSchema.parse(values)).toEqual(values);
});
