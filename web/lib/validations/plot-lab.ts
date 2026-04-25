import { z } from "zod";

export const formSchema = z.object({
  plotName: z.string().min(1),
  plotSkeletonMarkdown: z.string().min(1),
  storyEngineMarkdown: z.string().min(1),
});

export type FormValues = z.infer<typeof formSchema>;

export function makeEmptyFormValues(): FormValues {
  return {
    plotName: "",
    plotSkeletonMarkdown: "",
    storyEngineMarkdown: "",
  };
}
