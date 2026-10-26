from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict


class KnowledgeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True) # 可以把ORM数据转换成dict字典，通过 getattr()读属性
    id:int
    original_name:str
    source_path:str
    file_type:str
    visibility:str
    status:str
    chunk_count:int
    error_message:str | None
    created_by:int
    created_at:datetime
    updated_at:datetime

# 分页响应
class KnowledgeDocumentPage(BaseModel):
    items:List[KnowledgeDocumentOut]
    total:int
    page:int
    page_size:int

# 定义可见范围输入
from typing import Literal
class VisibilityIn(BaseModel):
    # Literal:限制只能传这两个参数，否则报错
    visibility:Literal["public", "internal"]

# 定义索引状态响应
class KnowledgeStatusOut(BaseModel):
    status: str
    chunks: int

# 请求与响应类型 只声明字段和类型
class AskRequest(BaseModel):
    question: str


class KnowledgeSource(BaseModel):
    index: int
    source: str
    page: int | None = None
    visibility: str


class AskResponse(BaseModel):
    answer: str
    sources: list[KnowledgeSource]
    retrieval_status: str