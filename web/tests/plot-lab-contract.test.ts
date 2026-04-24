import { formSchema } from "@/lib/validations/plot-lab";

test("plot lab form schema requires skeleton markdown", () => {
  const values = {
    plotName: "修罗场模板",
    plotSummaryMarkdown: "# 剧情定位\n修罗场模板\n",
    plotSkeletonMarkdown: "# 全书骨架\n- 开局铺垫\n",
    promptPackMarkdown: "# Shared Constraints\n不要洗白主角\n",
  };

  expect(formSchema.parse(values)).toEqual(values);
});
