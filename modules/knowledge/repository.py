# sql语句

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from modules.knowledge.model import KnowledgeDocument

from sqlalchemy import select


# 世界标准时间，伦敦时间 0时区时间
def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

# 创建记录
def create_document(db:Session,original_name:str,stored_name:str,
                    source_path:str,file_type:str,visibility:str,
                    created_by:int):
    now = utc_now()
    row=KnowledgeDocument(
        original_name=original_name,
        stored_name=stored_name,
        source_path=source_path,
        file_type=file_type,
        visibility=visibility,
        status="pending",
        chunk_count=0,
        error_message=None,
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    # 因为我们是保存数据，一旦提交就能够获取到id
    db.flush()
    return row

# 全库记录查询和状态更新
def all_documents(db: Session) -> list[KnowledgeDocument]:
        return list(db.scalars(select(KnowledgeDocument)).all())

def mark_indexed(row: KnowledgeDocument, chunks: int) -> None:
    row.status = "indexed"
    row.chunk_count = chunks
    row.error_message = None
    row.updated_at = utc_now()

def mark_error(row: KnowledgeDocument, message: str) -> None:
    row.status = "error"
    row.error_message = message[:2000]
    row.updated_at = utc_now()

# 查询数据库分页记录
from sqlalchemy import func
def list_documents(db:Session,page:int,page_size:int) :
    total=db.scalar(select(func.count()).select_from(KnowledgeDocument))
    rows=db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.id.desc())
                    .offset((page-1)*page_size).limit(page_size)).all()
    # rows每个元素都是 KnowledgeDocument ORM 实例
    # 不是dict，所以Pydantic需要from_attributes = True
    return list(rows),int(total)

# 按编号取得文档
def get_document(db: Session, document_id: int) -> KnowledgeDocument | None:
    # get是根据id获取一条数据的意思
    # select * from document where id=document_id
    return db.get(KnowledgeDocument, document_id)
