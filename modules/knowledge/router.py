from typing import Literal, Annotated

from fastapi import Form, APIRouter, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session

from database.connection import get_session
from modules.knowledge import service
from modules.user.permissions import require_permission
from modules.user.schemas import CurrentUser

router = APIRouter(prefix="/knowledge",tags=["知识库管理"])

from modules.knowledge.schemas import KnowledgeDocumentOut
# 上传知识文档路由
@router.post("/documents",response_model=KnowledgeDocumentOut, status_code=201)
async def uploaddocuments(
        # UploadFile 专门承接上传的文件
        file:Annotated[UploadFile,File()],
        visibility:Annotated[Literal["public", "internal"],Form()]="public",
        db:Session=Depends(get_session),
        user:CurrentUser=Depends(require_permission("kb.manage_docs"))
):
    # 调用sevice的函数，上传文件和保存文件信息
    return await service.upload_document2(db,file,visibility,user.id)

# 分页查询路由
from modules.knowledge.schemas import KnowledgeDocumentPage
from modules.knowledge import service
@router.get("/documents",response_model=KnowledgeDocumentPage)
def documents(page:int=Query(default=1,ge=1),
              page_size:int=Query(default=10, ge=1, le=100),
              db:Session=Depends(get_session),
              _:CurrentUser=Depends(require_permission("kb.manage_docs")),) -> KnowledgeDocumentPage:
    return service.get_documents(db,page,page_size)

# 修改文档权限的路由
from modules.knowledge.schemas import VisibilityIn
@router.patch("/documents/{document_id}/visibility",response_model=KnowledgeDocumentOut)
def update_visibility(
        document_id:int,
        data:VisibilityIn,
        db:Session=Depends(get_session),
        # “_”一个变量名。这个名字传递的信息是：我不需要这个数据本身
        _:CurrentUser=Depends(require_permission("kb.manage_docs"))
) -> KnowledgeDocumentOut:
    return service.change_visibility(db,document_id,data.visibility)

# 返回无正文的删除响应的路由
from fastapi import Response
@router.delete("/documents/{document_id}",status_code=204)
def remove_document(
        document_id:int,
        db:Session=Depends(get_session),
        _:CurrentUser=Depends(require_permission("kb.manage_docs"))
    )->Response:
    service.delete_document(db,document_id)
    return Response(status_code=204) # 204 删除成功

# 重建业务的路由
from modules.knowledge.schemas import KnowledgeStatusOut
@router.post("/reindex", response_model=KnowledgeStatusOut)
def reindex(
    db: Session = Depends(get_session),
    _: CurrentUser = Depends(require_permission("kb.manage_docs")),
    ) -> dict:
    return service.rebuild_index(db)

# 登录即可访问的状态路由
from modules.user.dependencies import get_current_user
@router.get("/status", response_model=KnowledgeStatusOut)
def index_status(_: CurrentUser = Depends(get_current_user)) -> dict:
    return service.get_index_status()

# 知识问答的路由
from modules.knowledge.rag.qa_service import answer_question
from modules.knowledge.schemas import AskRequest, AskResponse
from modules.user.permissions import allowed_visibilities
@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, user: CurrentUser = Depends(get_current_user)) -> dict:
    return answer_question(request.question, allowed_visibilities(user))