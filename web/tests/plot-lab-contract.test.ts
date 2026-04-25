import { formSchema } from "@/lib/validations/plot-lab";

test("plot lab form schema requires skeleton markdown", () => {
  const values = {
    plotName: "修罗场模板",
    plotSkeletonMarkdown: "# 全书骨架\n- 开局铺垫\n",
    storyEngineMarkdown: "# Story Engine Profile\n## genre_mother\n- xianxia\n",
  };

  expect(formSchema.parse(values)).toEqual(values);
});
