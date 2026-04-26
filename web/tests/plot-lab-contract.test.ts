import { formSchema } from "@/lib/validations/plot-lab";

test("plot lab form schema requires skeleton markdown", () => {
  const values = {
    plotName: "修罗场模板",
    plotSkeletonMarkdown: "# 全书骨架\n- 开局铺垫\n",
    storyEngineMarkdown: "# Plot Writing Guide\n## Core Plot Formula\n- 用压力迫使主角行动。\n",
  };

  expect(formSchema.parse(values)).toEqual(values);
});
