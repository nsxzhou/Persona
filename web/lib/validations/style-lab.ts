import { z } from "zod";

export const formSchema = z.object({
  styleName: z.string().min(1),
  styleSummaryMarkdown: z.string().min(1),
  promptPackMarkdown: z.string().min(1),
});

export type FormValues = z.infer<typeof formSchema>;

export function makeEmptyFormValues(): FormValues {
  return {
    styleName: "",
    styleSummaryMarkdown: "",
    promptPackMarkdown: "",
  };
}
