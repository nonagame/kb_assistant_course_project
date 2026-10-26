
from pathlib import Path
from uuid import uuid4
from threading import RLock

import traceback

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.config import settings
from modules.knowledge import repository
from modules.knowledge.model import KnowledgeDocument
from modules.knowledge.schemas import KnowledgeDocumentPage

from modules.knowledge.ingestion.loader import load_file, split_docs
from modules.knowledge.ingestion.build_index import index_document, index_documents, _add_chunks
from modules.knowledge.rag.vectorstore import delete_source, reset_collection,source_count


# 1.全局锁：保护 [文件系统 + 向量库 + DB状态] 的原子操作
# RLock()线程锁 ，控制多人同时操作，只有一个人能执行，顺次执行。为了避免高并发的数据错乱
INDEX_LOCK = RLock()

# 2. 常量统一管理
ALLOWED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}
# 定义10m，我们限定上传的文件最大10m
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB
VISIBILITIES = {"public", "internal"}



# 文件校验 安全路径解析，防止目录穿越攻击
def _document_path(source_path: str) -> Path:
    # ./data/docs
    root = settings.docs_dir.resolve()
    path = (root / source_path).resolve()
    if not path.is_relative_to(root) or path == root:
        raise HTTPException(status_code=400, detail="文档路径越出知识目录")
    return path

# 文件预校验与读取
async  def _read_upload(file:UploadFile):
    # file.filename 获取文件名称
    original_name = Path((file.filename or "").replace("\\", "/")).name
    # .suffix 获取文件后缀
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="只支持 txt、md、pdf、docx")
    if len(original_name) > 255:
        raise HTTPException(status_code=400, detail="文件名不能超过 255 个字符")
    # read 读取文件内容
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="上传文件不能为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件不能超过 10 MB")
    return original_name, suffix, content

def _check_visibility(visibility: str) -> None:
    if visibility not in {"public", "internal"}:
        raise HTTPException(status_code=400, detail="可见性只能是 public 或internal")

# 文件保存 原子化保存：先磁盘，后DB
def _save_document(db: Session, name: str, suffix: str,
                   content: bytes, visibility: str, user_id: int):
    # 1.存到本地   2534536sld3466.txt 新起文件名，避免覆盖
    stored_name = f"{uuid4().hex}{suffix}"
    # visibility==public /internal
    source_path = f"{visibility}/{stored_name}"
    # path = /data/docs/public/存储的文件名     path = /data/docs/internal/存储的文件名
    path = _document_path(source_path)
    # 如果没有这个父文件，我来创建
    path.parent.mkdir(parents=True, exist_ok=True)
    # 把数据写到文件
    path.write_bytes(content)
    # 2.存到mysql
    row = repository.create_document(
        db,
        original_name=name,
        stored_name=stored_name,
        source_path=source_path,
        file_type=suffix.lstrip("."),
        visibility=visibility,
        created_by=user_id,
    )
    db.commit()
    return row

# 统一处理单文件索引和全量重建
async def upload_document(db:Session,file:UploadFile,visibility:str,userid:int):
    # 1.上传文件
    name, suffix, content = await _read_upload(file)

    # 2.把信息存入数据库
    # return _save_document(db, name, suffix, content, visibility, userid)
    document: KnowledgeDocument = _save_document(db, name, suffix, content, visibility, userid)
    try:
        # 3.切片
        # 3.1 读取硬盘上的文件和内容  _document_path =  ./data/docs/public/eab51198bb5346da9ad94b94b89ae534.md
        # 读取硬盘文件，转成一个charmdb能存的document   documents = []
        documents = load_file(_document_path(document.source_path), settings.docs_dir)
        # 切片存储  切完后的列表数据
        chunks = split_docs(documents)

        # 把切的块存入charomdb
        _add_chunks(chunks)

        document.chunk_count = len(chunks)
        document.status = "indexed" if chunks else "error"
        document.error_message = None if chunks else "未读取到可索引文本，请检查文件"
        db.commit()
    except Exception as exc:
        db.rollback()
        document.status = "error"
        document.chunk_count = 0
        document.error_message = "文档解析失败，请检查文件格式和编码"
        db.commit()
        raise HTTPException(status_code=503, detail=document.error_message) from exc
    db.refresh(document)

    # 4.存入chromdb
    return document

# 日常增量路径 增量索引核心：解析 -> 切块 -> 入库 -> 更新状态
def _index_saved_document(db: Session, row) -> int:
    source_path = row.source_path
    try:
        # 先清掉该来源可能残留的旧块，再只索引当前文件。
        delete_source(source_path)
        chunks = index_document(_document_path(source_path))
        if chunks:
            # 告诉mysql存了多少片
            repository.mark_indexed(row, chunks)
        else:
            row.chunk_count = 0
            repository.mark_error(row, "未读取到该文档的可索引文本，请检查文件")
        db.commit()
        return chunks
    except Exception as exc:
        db.rollback()
        try:
            # 防止 add_documents 中途失败后留下当前来源的半截数据。
            delete_source(source_path)
        except Exception:
            print(f"[ERROR] 索引文档 {row.id} 失败")
            traceback.print_exc()
        row.chunk_count = 0
        repository.mark_error(row, "当前文件索引失败，请检查解析文件、Ollama 与Chroma")
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="文档变更已保存，但当前文件索引失败；修复后调用 POST/knowledge/reindex",
        ) from exc

# 全量重建
# 扫描整个目录、重建 collection，再逐份统计来源块数并回写 MySQL
def _refresh_index(db: Session) -> int:
    try:
        chunks = index_documents()
        for row in repository.all_documents(db):
            count = source_count(row.source_path)
            if count:
                repository.mark_indexed(row, count)
            else:
                row.chunk_count = 0
                repository.mark_error(row, "未读取到该文档的可索引文本，请检查文件")
        db.commit()
        return chunks
    except Exception as exc:
        db.rollback()
        try:
            # 全量重建失败时不保留可能只写入一部分的 collection。
            reset_collection()
        except Exception:
            pass
        for row in repository.all_documents(db):
            row.chunk_count = 0
            repository.mark_error(row, "索引重建失败，请检查解析文件及索引服务后重新构建")
        db.commit()
        raise HTTPException(
                status_code=503,
                detail="全量索引重建失败；修复后再次调用 POST /knowledge/reindex",
        ) from exc

# 最终增量版上传函数
async def upload_document2(db: Session, upload: UploadFile, visibility: str,user_id: int):
    _check_visibility(visibility)
    name, suffix, content = await _read_upload(upload)
    with INDEX_LOCK:
        row = _save_document(db, name, suffix, content, visibility, user_id)
        try:
            _index_saved_document(db, row)
        except HTTPException :
            pass
        db.refresh(row)
        return row

# 封装分页结果
def get_documents(db:Session,page:int,page_size:int) :
    rows,total=repository.list_documents(db, page, page_size)
    return KnowledgeDocumentPage(items=rows,total=total,page_size=page_size,page=page)

# 移动文件并增量更新该文档索引
# 修改可见性：物理移动文件 + 向量库元数据更新
def change_visibility(db:Session,document_id:int,visibility:str):
    with INDEX_LOCK:
        row=repository.get_document(db,document_id)
        # 一行数据
        if row is None:
            raise HTTPException(status_code=404,detail="文档不存在")

        old_source_path=row.source_path
        # 找到文件存到硬盘的路径
        old_path=_document_path(old_source_path)
        if not old_path.is_file():
            raise HTTPException(status_code=409, detail="文档文件缺失，请删除记录后重新上传")
        if row.visibility==visibility:
            return row

        # 用户想改的硬盘路径
        new_path=_document_path(f"{visibility}/{row.stored_name}")
        if new_path.exists():
            raise HTTPException(status_code=409, detail="目标文件已经存在")
        try:
            # 删除chromdb中的文档数据
            old_vector_count=delete_source(old_source_path)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="索引服务不可用，本次可见范围修改未执行",
            )from exc
        new_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # 硬盘移动旧文件到新位置
            old_path.replace(new_path)
            row.visibility=visibility
            row.source_path=new_path.relative_to(settings.docs_dir.resolve()).as_posix()
            row.status="pending"
            row.chunk_count=0
            row.error_message=None
            db.commit()
        except Exception as exc:
            db.rollback()
            if new_path.exists():
                new_path.replace(old_path)
            if old_vector_count and old_path.is_file():
                try:
                    # 如果报错，之前冲chromdb删除的数据，再恢复回来(重新构建)。
                    index_document(old_path)
                except Exception:
                    print("[ERROR] 可见性变更回滚向量库失败")
                    import traceback;traceback.print_exc()
            raise HTTPException(status_code=500, detail="文件移动失败") from exc
        # 第一，把文件加载到chrmadb，第二，更新mysql数据中的数据
        _index_saved_document(db, row)
        db.refresh(row)
        return row


# 增量删除业务
def delete_document(db: Session, document_id: int) -> None:
    with INDEX_LOCK:
        row = repository.get_document(db, document_id)
        if row is None:
            raise HTTPException(status_code=404, detail="文档不存在")

        source_path = row.source_path
        path = _document_path(source_path)
        backup = path.with_suffix(path.suffix + f".{uuid4().hex}.pending_delete")
        try:
            deleted_vectors = delete_source(source_path)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="索引服务不可用，本次删除未执行",
            ) from exc

        try:
            if path.exists():
                path.replace(backup)
                db.delete(row)
                db.commit()
        except Exception as exc:
            # 如果DB提交失败，必须恢复文件并重建向量。
            db.rollback()
            if backup.exists():
                backup.replace(path)
            if deleted_vectors and path.is_file():
                try:
                    index_document(path)
                except Exception:
                    # 只有在db.commit()成功后，才会执行到这里，安全删除备份文件。
                    print("[ERROR] 删除回滚向量库失败")
                    traceback.print_exc()
            raise HTTPException(status_code=500, detail="数据库删除失败") from exc
    if backup.exists():
        backup.unlink(missing_ok=True)

# 重建业务
def rebuild_index(db: Session) -> dict:
    with INDEX_LOCK:
        return {"status": "ok", "chunks": _refresh_index(db)}

# 读取集合计数
from modules.knowledge.rag.vectorstore import collection_count
def get_index_status() -> dict:
    try:
        return {"status": "ok", "chunks": collection_count()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="索引服务不可用") from exc