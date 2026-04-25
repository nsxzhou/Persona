import { z } from "zod";

export const formSchema = z.object({
  styleName: z.string().min(1),
  voiceProfileMarkdown: z.string().min(1),
});

export type FormValues = z.infer<typeof formSchema>;

export function makeEmptyFormValues(): FormValues {
  return {
    styleName: "",
    voiceProfileMarkdown: "",
  };
}
