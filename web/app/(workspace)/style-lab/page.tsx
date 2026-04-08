import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function StyleLabPage() {
  return (
    <Card className="bg-[linear-gradient(135deg,rgba(255,255,255,0.95),rgba(245,238,229,0.92))]">
      <CardHeader>
        <CardTitle>Style Lab</CardTitle>
        <CardDescription>当前版本先冻结信息架构。后续会在这里接入 TXT 上传、切片任务、LangGraph 工作流与进度反馈。</CardDescription>
      </CardHeader>
      <CardContent className="text-sm leading-7 text-stone-600">
        这次任务只完成基础平台，所以这里保留为占位页，确保导航结构和后续扩展点已经固定。
      </CardContent>
    </Card>
  );
}
