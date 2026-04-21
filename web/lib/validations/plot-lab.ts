import { z } from "zod";

export const formSchema = z.object({
  plotName: z.string().min(1),
  plotSummaryMarkdown: z.string().min(1),
  promptPackMarkdown: z.string().min(1),
});

export type FormValues = z.infer<typeof formSchema>;

export function makeEmptyFormValues(): FormValues {
  return {
    plotName: "",
    plotSummaryMarkdown: "",
    promptPackMarkdown: "",
  };
}
