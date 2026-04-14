"use client";

import { useEffect, useRef, useState } from "react";
import { Project } from "@/lib/types";
import { api } from "@/lib/api";
import { ArrowLeft, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

export function ZenEditorView({
  project,
  activeProfileName,
}: {
  project: Project;
  activeProfileName?: string;
}) {
  const [content, setContent] = useState(project.content || "");
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 防抖保存
  useEffect(() => {
    if (content === project.content) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      setIsSaving(true);
      try {
        await api.updateProject(project.id, { content });
      } catch (e) {
        console.error("Failed to save content", e);
        toast.error("自动保存失败");
      } finally {
        setIsSaving(false);
      }
    }, 1000);

    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    };
  }, [content, project.id, project.content]);

  // 触发续写
  const handleGenerate = async () => {
    if (!project.style_profile_id) {
      toast.error("项目未挂载风格档案，无法进行续写。请先在项目设置中选择风格档案。");
      return;
    }
    if (isGenerating) return;

    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPosition = textarea.selectionStart;
    const textBeforeCursor = content.substring(0, cursorPosition);

    setIsGenerating(true);

    try {
      const response = await fetch(`/api/v1/projects/${project.id}/editor/complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text_before_cursor: textBeforeCursor }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "请求失败");
      }

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      let currentGenerated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.substring(6);
            if (!dataStr) continue;
            try {
              const parsed = JSON.parse(dataStr);
              currentGenerated += parsed;
              
              // 实时更新内容，将生成的文本插入到光标位置
              setContent((prev) => {
                const before = textBeforeCursor;
                const after = prev.substring(cursorPosition);
                return before + currentGenerated + after;
              });

            } catch (e) {
              console.error("Failed to parse SSE data:", dataStr);
            }
          } else if (line.startsWith("event: error")) {
            throw new Error("生成过程中发生错误");
          }
        }
      }
      
      // Let the cursor move to the end of the newly generated text
      requestAnimationFrame(() => {
        if (textarea) {
          const newPos = cursorPosition + currentGenerated.length;
          textarea.setSelectionRange(newPos, newPos);
          textarea.focus();
        }
      });
    } catch (e: any) {
      console.error(e);
      toast.error(e.message || "续写失败，请稍后重试");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "j") {
      e.preventDefault();
      handleGenerate();
    }
  };

  return (
    <div className="flex flex-col h-screen w-full bg-background text-foreground">
      {/* 顶部导航 */}
      <header className="flex items-center justify-between px-6 py-4 border-b shrink-0">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href={`/projects/${project.id}`}>
              <ArrowLeft className="w-5 h-5" />
            </Link>
          </Button>
          <h1 className="text-lg font-medium">{project.name}</h1>
        </div>

        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>保存中...</span>
              </>
            ) : (
              <span>已保存</span>
            )}
          </div>
          <div className="flex items-center gap-2 bg-muted/50 px-3 py-1.5 rounded-md">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="font-medium">
              {activeProfileName ? activeProfileName : "未挂载风格"}
            </span>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleGenerate} 
            disabled={isGenerating || !project.style_profile_id}
            className="gap-2"
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            AI 续写 (Cmd+J)
          </Button>
        </div>
      </header>

      {/* 编辑区 */}
      <main className="flex-1 overflow-hidden relative flex justify-center bg-muted/20">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="开始创作... (按 Cmd+J 进行 AI 续写)"
          className="w-full max-w-4xl h-full p-8 md:p-12 resize-none bg-transparent outline-none text-lg leading-relaxed shadow-none border-none focus:ring-0 text-foreground/90 placeholder:text-muted-foreground/50"
          style={{
            fontFamily: "var(--font-serif), serif",
          }}
        />
      </main>
    </div>
  );
}