import { describe, expect, test } from "vitest";

import { parsePromptTraceMarkdown } from "@/lib/prompt-trace-parser";

const traceMarkdown = `# Prompt Trace

| Field | Value |
| --- | --- |
| Run ID | \`run-1\` |
| Calls | 1 |
| Completed calls | 1 |
| Failed calls | 0 |
| Total input chars | 41 |
| Contains truncation marker | no |

## Call summary

| # | Stage | Mode | Model | Input chars | Output chars | Truncated | Error |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| 1 | generating | immersion | gpt-test | 41 | 2 | no | - |

## Call 1 - generating / immersion

| Field | Value |
| --- | --- |
| Intent | \`selection_rewrite\` |
| Stage | \`generating\` |
| Mode | \`immersion\` |
| Provider | \`Primary\` |
| Provider ID | \`provider-1\` |
| Model | \`gpt-test\` |
| Started at | \`2026-05-07T10:00:00.000+00:00\` |
| Completed at | \`2026-05-07T10:00:00.042+00:00\` |
| Duration | 42 ms |
| Total input chars | 41 |
| System chars | 4 |
| User chars | 37 |
| Output chars | 2 |
| Contains truncation marker | no |

### System message

- Chars: 4
- Contains truncation marker: no

\`\`\`
系统提示
\`\`\`

### User message

- Chars: 37
- Contains truncation marker: no

\`\`\`\`
包含 fence:
\`\`\`python
print(1)
\`\`\`
\`\`\`\`

### Output excerpt

\`\`\`
OK
\`\`\`
`;

describe("parsePromptTraceMarkdown", () => {
  test("parses current prompt trace markdown format without losing fences", () => {
    const parsed = parsePromptTraceMarkdown(traceMarkdown);

    expect(parsed).not.toBeNull();
    expect(parsed?.summary["Run ID"]).toBe("run-1");
    expect(parsed?.summary.Calls).toBe("1");
    expect(parsed?.callSummary[0]).toMatchObject({
      callIndex: "1",
      stage: "generating",
      mode: "immersion",
      model: "gpt-test",
    });
    expect(parsed?.calls[0].metadata.Model).toBe("gpt-test");
    expect(parsed?.calls[0].segments).toHaveLength(3);
    expect(parsed?.calls[0].segments[1].content).toBe("包含 fence:\n```python\nprint(1)\n```");
    expect(parsed?.calls[0].segments[2].content).toBe("OK");
  });

  test("keeps structural-looking headings inside fenced message content", () => {
    const parsed = parsePromptTraceMarkdown(
      traceMarkdown.replace(
        "系统提示",
        "系统提示\n\n### inner heading\n\n## Call fake - x / y\n\n仍然属于 System message",
      ),
    );

    expect(parsed).not.toBeNull();
    expect(parsed?.calls).toHaveLength(1);
    expect(parsed?.calls[0].segments).toHaveLength(3);
    expect(parsed?.calls[0].segments[0].content).toBe(
      "系统提示\n\n### inner heading\n\n## Call fake - x / y\n\n仍然属于 System message",
    );
    expect(parsed?.calls[0].segments[2].content).toBe("OK");
  });

  test("parses output fallback text for failed calls", () => {
    const parsed = parsePromptTraceMarkdown(
      traceMarkdown
        .replace("| 1 | generating | immersion | gpt-test | 41 | 2 | no | - |", "| 1 | generating | immersion | gpt-test | 41 | - | no | boom |")
        .replace("| Output chars | 2 |", "| Output chars | - |\n| Error | `boom` |")
        .replace("```\nOK\n```", "Call failed before producing output: `boom`"),
    );

    expect(parsed).not.toBeNull();
    expect(parsed?.calls[0].metadata.Error).toBe("boom");
    expect(parsed?.calls[0].segments[2]).toMatchObject({
      title: "Output excerpt",
      kind: "output",
      content: "Call failed before producing output: `boom`",
      fallbackText: "Call failed before producing output: `boom`",
    });
  });

  test("returns null for unsupported markdown instead of guessing", () => {
    expect(parsePromptTraceMarkdown("# Prompt Trace\n\n## Call 1")).toBeNull();
    expect(parsePromptTraceMarkdown("# Other\n\nbody")).toBeNull();
    expect(
      parsePromptTraceMarkdown(
        traceMarkdown
          .replace("| Field | Value |", "| Value | Field |")
          .replace("### System message", "### Assistant message"),
      ),
    ).toBeNull();
  });
});
