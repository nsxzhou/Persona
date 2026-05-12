 "use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function PageLoading({ title = "正在载入 Persona..." }: { title?: string }) {
  return (
    <div className="motion-page flex min-h-[40vh] items-center justify-center" aria-busy="true" aria-live="polite">
      <Card className="w-full max-w-lg animate-scale-in">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>请稍候，系统正在同步当前状态。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="h-3 w-2/3 animate-pulse rounded-sm bg-muted" />
          <div className="h-3 w-full animate-pulse rounded-sm bg-muted motion-delay-1" />
          <div className="h-3 w-4/5 animate-pulse rounded-sm bg-muted motion-delay-2" />
        </CardContent>
      </Card>
    </div>
  );
}

export function PageError({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="motion-page flex min-h-[40vh] items-center justify-center">
      <Card className="w-full max-w-lg animate-scale-in border-destructive/20">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{message}</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          请检查后端服务与环境变量是否已正确配置。
        </CardContent>
      </Card>
    </div>
  );
}
