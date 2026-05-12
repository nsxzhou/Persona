import type { DiffBlock } from "@/lib/diff-utils";
import { cn } from "@/lib/utils";

export function DiffColumn({
  title,
  blocks,
  side,
  empty,
  emptyText,
}: {
  title: string;
  blocks: DiffBlock[];
  side: "left" | "right";
  empty: boolean;
  emptyText: string;
}) {
  return (
    <div className="flex min-h-0 flex-col overflow-hidden rounded-md border bg-background">
      <div className="border-b px-3 py-2">
        <span className="text-xs font-medium text-muted-foreground">{title}</span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto bg-muted/20 p-3 font-mono text-sm leading-relaxed">
        {empty ? (
          <span className="text-muted-foreground italic">{emptyText}</span>
        ) : (
          <DiffBlocks blocks={blocks} side={side} />
        )}
      </div>
    </div>
  );
}

function DiffBlocks({ blocks, side }: { blocks: DiffBlock[]; side: "left" | "right" }) {
  return (
    <div className="whitespace-pre-wrap break-words">
      {blocks.map((block, index) =>
        block.lines.map((line, lineIndex) => (
          <DiffLineRow
            key={`${index}-${lineIndex}`}
            type={line.type}
            text={line.text}
            hideAdded={side === "left"}
            hideRemoved={side === "right"}
          />
        )),
      )}
    </div>
  );
}

function DiffLineRow({
  type,
  text,
  hideAdded,
  hideRemoved,
}: {
  type: "added" | "removed" | "unchanged";
  text: string;
  hideAdded?: boolean;
  hideRemoved?: boolean;
}) {
  if (type === "added" && hideAdded) return null;
  if (type === "removed" && hideRemoved) return null;
  const marker = type === "added" ? "+" : type === "removed" ? "-" : " ";
  return (
    <div
      className={cn(
        "flex gap-2 px-1",
        type === "added" && "bg-emerald-500/15 text-emerald-800",
        type === "removed" && "bg-red-500/15 text-red-800 line-through",
      )}
    >
      <span className="select-none text-muted-foreground">{marker}</span>
      <span className="flex-1">{text || " "}</span>
    </div>
  );
}
