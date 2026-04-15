from __future__ import annotations

from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.provider_configs import ProviderSummary


ProjectStatus = Literal["draft", "active", "paused"]


class ProjectCreate(BaseModel):
    # 项目名称：字符串类型，长度限制1-120字符
    # Field是Pydantic的字段配置函数，用于添加验证规则和元数据
    name: str = Field(min_length=1, max_length=120)

    # 项目描述：默认空字符串，最大长度4000字符
    description: str = Field(default="", max_length=4000)

    # 项目状态：只能是ProjectStatus定义的三个值之一，默认是draft
    status: ProjectStatus = "draft"

    # 默认提供商ID：必填字段
    default_provider_id: str

    # 默认模型：可选字段，可以为None
    # str | None 是Python 3.10+的语法，表示"字符串或者空"
    default_model: str | None = None

    # 风格配置ID：可选字段
    style_profile_id: str | None = None

    # 故事圣经各区块
    inspiration: str = ""
    world_building: str = ""
    characters: str = ""
    outline_master: str = ""
    outline_detail: str = ""
    story_bible: str = ""

    # 项目正文内容
    content: str = ""


class ProjectUpdate(BaseModel):
    # 注意这里的类型是 str | None，默认值是 None
    # 这表示用户可以传这个字段，也可以不传
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    status: ProjectStatus | None = None
    default_provider_id: str | None = None
    default_model: str | None = None
    style_profile_id: str | None = None
    inspiration: str | None = None
    world_building: str | None = None
    characters: str | None = None
    outline_master: str | None = None
    outline_detail: str | None = None
    story_bible: str | None = None
    content: str | None = None


class ProjectResponse(BaseModel):
    # 启用ORM模式：允许直接从SQLAlchemy对象创建这个Schema实例
    model_config = ConfigDict(from_attributes=True)

    # 项目ID
    id: str
    # 项目名称
    name: str
    # 项目描述
    description: str
    # 项目状态
    status: ProjectStatus
    # 默认提供商ID
    default_provider_id: str
    # 默认模型
    default_model: str
    # 风格配置ID
    style_profile_id: str | None
    # 故事圣经各区块
    inspiration: str
    world_building: str
    characters: str
    outline_master: str
    outline_detail: str
    story_bible: str
    # 项目正文内容
    content: str
    # 归档时间 - 没有归档就是None
    archived_at: datetime | None
    # 创建时间 - 自动生成，只读
    created_at: datetime
    # 更新时间 - 自动生成，只读
    updated_at: datetime
    # 嵌套的提供商信息 - 直接引用另一个Schema
    # Pydantic会自动递归序列化嵌套的对象
    provider: ProviderSummary


class EditorCompletionRequest(BaseModel):
    text_before_cursor: str


class SectionGenerateRequest(BaseModel):
    section: str = Field(description="要生成的区块名称")
    inspiration: str = ""
    world_building: str = ""
    characters: str = ""
    outline_master: str = ""
    outline_detail: str = ""
    story_bible: str = ""


class BibleUpdateRequest(BaseModel):
    current_bible: str
    new_content_context: str = Field(description="本次新生成的文本")


class BibleUpdateResponse(BaseModel):
    proposed_bible: str


class BeatGenerateRequest(BaseModel):
    text_before_cursor: str
    story_bible: str = ""
    outline_detail: str = ""
    num_beats: int = Field(default=8, ge=3, le=15)


class BeatGenerateResponse(BaseModel):
    beats: list[str]


class BeatExpandRequest(BaseModel):
    text_before_cursor: str
    story_bible: str = ""
    outline_detail: str = ""
    beat: str
    beat_index: int
    total_beats: int
    preceding_beats_prose: str = ""


class ConceptGenerateRequest(BaseModel):
    inspiration: str = Field(min_length=1, max_length=8000, description="用户灵感描述文本")
    provider_id: str = Field(description="AI 服务商 ID")
    model: str | None = Field(default=None, description="可选模型覆盖")
    count: int = Field(default=3, ge=1, le=5, description="生成候选数量")


class ConceptItem(BaseModel):
    title: str
    synopsis: str


class ConceptGenerateResponse(BaseModel):
    concepts: list[ConceptItem]
