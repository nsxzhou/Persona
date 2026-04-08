import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function PageLoading({ title = "正在载入 Persona..." }: { title?: string }) {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>请稍候，系统正在同步当前状态。</CardDescription>
        </CardHeader>
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
    <div className="flex min-h-[40vh] items-center justify-center">
      <Card className="w-full max-w-lg border-red-200">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{message}</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-stone-500">
          请检查后端服务与环境变量是否已正确配置。
        </CardContent>
      </Card>
    </div>
  );
}

