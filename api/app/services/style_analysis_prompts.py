from typing import Any
import json
from app.schemas.style_analysis_jobs import SECTION_TITLES

SHARED_ANALYSIS_RULES = """
你必须遵守以下规则：
1. 所有结论必须证据优先，不得编造不存在的设定、说话人或风格特征。
2. 输出必须使用中文简体，并严格匹配提供的结构化输出 schema。
3. 如果证据不足，必须明确使用低置信或弱判断，不得伪装成确定结论。
4. 关注文本类型、索引方式、噪声、批处理条件，并在后续分析中保持一致。
5. 3.1 到 3.12 的专题不能缺失，但某一节证据稀少时允许给出“当前样本中证据有限”的说明。
""".strip()

def _format_sections() -> str:
    return "\n".join(f"- {section} {title}" for section, title in SECTION_TITLES)

def build_chunk_analysis_prompt(
    *,
    chunk: str,
    chunk_index: int,
    classification: dict[str, Any],
    chunk_count: int,
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行分块分析阶段。请基于当前 chunk 的文本生成结构化输出。\n"
        "要求：\n"
        "1. sections 必须覆盖 3.1 到 3.12。\n"
        "2. 每节可以只有 1-3 条 finding；证据不足时仍保留该节并降低置信度。\n"
        "3. excerpt 必须来自样本文本，不得编造。\n"
        "4. confidence 只能是 high/medium/low。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"当前 chunk：{chunk_index + 1}/{chunk_count}\n"
        f"章节结构：\n{_format_sections()}\n\n"
        f"样本文本：\n{chunk}"
    )

def build_merge_prompt(
    *,
    chunk_analyses: list[dict[str, Any]],
    classification: dict[str, Any],
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行全局聚合阶段。请把多个 chunk 的分析结果合并为统一结构化输出。\n"
        "要求：同义归并、重复证据去重、弱判断保留、多说话人差异不抹平。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"章节结构：\n{_format_sections()}\n\n"
        f"待合并结果：\n{json.dumps(chunk_analyses, ensure_ascii=False)}"
    )

def build_report_prompt(
    *,
    merged_analysis: dict[str, Any],
    classification: dict[str, Any],
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在把聚合结果整理成最终分析报告。sections 必须覆盖 3.1 到 3.12。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"聚合结果：\n{json.dumps(merged_analysis, ensure_ascii=False)}"
    )

def build_style_summary_prompt(
    *,
    report: dict[str, Any],
    style_name: str,
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在从完整分析报告提炼可编辑风格摘要。"
        "不要引入报告中不存在的结论；尽量高密度、可用于后续生成。\n\n"
        f"风格名称：{style_name}\n"
        f"分析报告：\n{json.dumps(report, ensure_ascii=False)}"
    )

def build_prompt_pack_prompt(
    *,
    report: dict[str, Any],
    style_summary: dict[str, Any],
) -> str:
    return (
        "你是一位小说写作 prompt 编排器。"
        "请基于完整分析报告和当前风格摘要，生成一个全局可复用的风格母 prompt 包。"
        "不要绑定具体项目剧情，不要引入报告中没有的结论。\n\n"
        f"分析报告：\n{json.dumps(report, ensure_ascii=False)}\n\n"
        f"当前风格摘要：\n{json.dumps(style_summary, ensure_ascii=False)}"
    )
