from __future__ import annotations

import re

from pydantic import BaseModel

from app.core.domain_errors import UnprocessableEntityError
from app.prompts.common import REGENERATION_GUIDANCE, append_regeneration_context
from app.prompts.novel_shared import append_profile_blocks, get_hook_framework
from app.schemas.prompt_profiles import GenerationProfile


class ConceptCard(BaseModel):
    title: str
    synopsis: str


def parse_concept_response(raw: str, expected_count: int) -> list[ConceptCard]:
    text = raw.strip()
    concepts: list[ConceptCard] = []
    for part in re.split(r"^###\s+", text, flags=re.MULTILINE):
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n", 1)
        if len(lines) < 2:
            continue
        title = re.sub(r"^\d+[\.、\s]+", "", lines[0].strip())
        synopsis = lines[1].strip()
        if title and synopsis:
            concepts.append(ConceptCard(title=title, synopsis=synopsis))
    if not concepts:
        raise UnprocessableEntityError("AI 返回的格式无法解析，请重试")
    return concepts[:expected_count]


_CONCEPT_GENERATE_SYSTEM_TEMPLATE = (
    "你是一位深耕网文市场（起点、番茄等平台）的资深策划编辑。\n\n"
    "你需要根据用户给出的灵感描述，先提炼小说核心DNA，再产出指定数量的小说概念卡。"
    "核心DNA公式必须在内部约束所有概念：当[主角+身份]遭遇[核心事件]，必须[关键行动]，否则[灾难后果]；"
    "与此同时，[隐藏的更大危机]正在发酵。"
    "这些概念卡必须共享同一故事主轴，是同一本书的不同包装方向，"
    "不能写成三本完全不同的小说。"
    "每个概念包含标题和一段可直接用作项目简介的简介。\n\n"
    "## 生成前的隐式判断\n"
    "在输出前，先在内部完成以下判断，但不要把判断过程写出来：\n"
    "- 主角是谁，当前最抓人的身份和处境是什么\n"
    "- 读者为什么会点进来并继续追，这本书当前的主驱动轴是什么\n"
    "- 真正能支撑点击的核心卖点是什么\n"
    "- 显性冲突、潜在危机、主角核心驱动力是否能组成同一个核心DNA\n"
    "- 简介是否适合用短标签开头\n\n"
    "## 差异化规则\n"
    "所有概念卡都必须保留同一故事主轴，只能改变卖点切口与包装方式。\n"
    "差异优先体现在主角切口、局势压力、关系张力、破局手段或兑现方式。\n"
    "可变化的驱动入口包括：升级/权力扩张、局势反压、身份逆转、资源掠夺、关系张力、暧昧兑现。\n"
    "不要为了拉开差异，硬把同一主轴写成更大的体系、更多的势力或更高的世界层级。\n"
    "三张卡的差异必须围绕主驱动轴做不同包装，不是只换标题和设定表皮。\n"
    "建议分别优先突出以下入口：\n"
    "- 概念 1：主角身份与开局处境最抓人\n"
    "- 概念 2：机制 / 金手指 / 核心玩法最抓人\n"
    "- 概念 3：人物关系 / 对抗局面 / 情绪钩子最抓人\n\n"
    "## 标题规则\n"
    "- 标题要符合现代网文命名气质，可以短狠、反问、反差、轻俏，但不要冗长解释\n"
    "- 禁止平庸标题如「我的XXX之旅」「关于XXX这件事」\n"
    "- 标题参考气质：道诡异仙、娱乐春秋、反派：仙子哪里逃？、"
    "圣女沉沦？我的许愿系统不对劲！、让你代管宗门，怎么全成大帝了\n\n"
    "## 简介规则\n"
    "- 字数控制在 150-260 字左右，按 1-3 个自然段组织\n"
    "- 宁可短而抓人，也不要为了显得厚重而写成长简介\n"
    "- 按题材决定是否使用短标签开头；强爽文、系统文、多女主、修罗场题材可用短标签，"
    "权谋、悬疑、偏剧情型题材可直接正文开场\n"
    "- 第一段尽快交代主角是谁、正被什么局面逼住、引爆事件是什么\n"
    "- 中段把卖点落在事件、机制、关系或局势上，不要只喊口号，也不要堆设定规模\n"
    "- 结尾保留继续读的欲望，但不要写成广告标语或硬拗金句\n\n"
    "## 写法要求\n"
    "- 像小说简介，不像广告投流文案\n"
    "- 先写人和局，再写大词，不要空泛开场\n"
    "- 可以有网文味和爽点，但不要油腻、不要连续宣传腔\n"
    "- 不要连续堆砌模板反转句、排比句、四字词和宣言句\n"
    "- 不要把简介写成金句合集\n"
    "- 不要为了显得炸裂而生造宏大名词、尊号和设定术语\n"
    "- 标签如果使用，只能压缩卖点，不能替代正文\n\n"
    "## 示例学习\n"
    "以下示例仅用于学习标题气质、简介节奏与卖点组织方式。"
    "仅学习标题气质、简介节奏与卖点组织方式，"
    "不要照搬示例中的设定、身份、名词、人物关系和具体桥段。\n\n"
    "### 示例 1（优点：主角处境明确，卖点落在关系和场景上）\n"
    "### 反派：仙子哪里逃？\n"
    "【反派+多女主+日常+修罗场+不舔狗】 陈善知穿越到了一款多女主RPG游戏里，成了大反派镇国侯的纨绔短命世子。"
    "这款游戏里，绝大部分奇遇都和某个女主绑定，只要把好感刷到最高，就能拿到对应奖励。"
    "而陈善知脑海里，偏偏装着整个游戏攻略和各个女主的详细信息。\n\n"
    "为了活命，他只能比原主角更早一步下场，想尽办法把那些本不该站在自己这边的人，全都拉到自己阵营。"
    "可他越往前走，越发现这不只是刷好感那么简单，朝局、宗门、皇权和主角团的命运，早就被搅成了一锅滚油。\n\n"
    "等到原本的主角修炼有成，上门寻仇时，却只看到妹妹替陈善知剥葡萄，女剑仙给他捏腿，连高高在上的女皇都靠在他怀里。"
    "陈善知看着目眦欲裂的对方，笑得云淡风轻：抱歉，在这游戏里，修炼没用。\n\n"
    "### 示例 2（优点：机制离谱，但叙述口气自然）\n"
    "### 圣女沉沦？我的许愿系统不对劲！\n"
    "【爽文+杀伐果断+伪无敌+许愿+艺术+多红颜】 宁易宿慧觉醒，穿越到武道为尊的大周王朝，得到了【大艺术家许愿系统】。"
    "这个系统的规则很简单：只要学习艺术，就能提升武道神通境界，并得到许愿点进行许愿。"
    "问题在于，它实现愿望的方式，总带着一点不太正经的味道。\n\n"
    "他想要金钱，系统安排他碰瓷龙宫龙女；他想要顶级功法，系统直接送来要和圣女一起修的双修秘典；"
    "他说书、酿酒、吟诗、弹琴，本想混日子，却一次次把自己推到风口浪尖。"
    "在这个妖庭环伺、魔道猖獗的时代里，人人都在苦修争命，唯独他靠着一套离谱系统，把艺术玩成了通天大道。\n\n"
    "直到某一日，宁易横空出世，一拳震塌五行，翻转阴阳，所有人才终于意识到："
    "这个看似不务正业的少年，早就用最不正经的方式，走上了最不讲道理的无敌路。\n\n"
    "### 示例 3（优点：轻佻有趣，但不是搞笑文案）\n"
    "### 娱乐春秋\n"
    "现代人闯进架空异界，面对的不只是武道百家，还有一整个只知道苦修争雄的世界。"
    "别人练武求名，他却偏要用戏曲、话术、娱乐、审美和知识，把江湖、宗门乃至朝局一起搅动。"
    "这类简介的优点，不在于靠夸张词炸人，而在于主角方法论够新，语气够松，卖点仍然落在他能怎么改变这个世界。\n\n"
    "若用户灵感不含系统、多女主、修罗场、反派等元素，不得因为示例出现过就强行加入。\n\n"
    "{hook_framework}\n\n"
    "## 输出格式\n"
    "请使用 Markdown 格式输出，每个概念采用以下结构：\n"
    "### [标题]\n"
    "[简介]\n\n"
    "直接输出内容，不要添加任何其他前言或总结、也不要输出任何序号。"
)


def build_concept_generate_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    regenerating: bool = False,
) -> str:
    parts: list[str] = []
    if style_prompt:
        parts.append("# Style Prompt Pack（风格约束）\n\n")
        parts.append(style_prompt.strip())
        parts.append("\n\n---\n")
    append_profile_blocks(
        parts,
        style_prompt=None,
        plot_prompt=plot_prompt,
        plot_usage=(
            "概念生成阶段也必须应用已选 Plot/Style Profile；"
            "标题和简介要体现 Plot Pack 的主驱动轴、读者追读问题和角色功能位。"
        ),
        generation_profile=generation_profile,
    )
    hook_framework = get_hook_framework(generation_profile)
    parts.append(_CONCEPT_GENERATE_SYSTEM_TEMPLATE.format(hook_framework=hook_framework))
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_concept_generate_user_message(
    inspiration: str,
    count: int,
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    parts: list[str] = [f"请根据以下灵感描述生成 {count} 个小说概念：\n\n{inspiration}"]
    append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)
