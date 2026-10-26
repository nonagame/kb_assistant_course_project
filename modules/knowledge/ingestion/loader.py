from pathlib import Path
import hashlib
import docx
from langchain_core.documents import Document
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.config import settings

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".md", ".txt"}
VISIBILITIES = {"public", "internal"}

def _visibility(path: Path, docs_dir: Path) -> str:
    relative = path.relative_to(docs_dir)
    first_part = relative.parts[0].lower() if len(relative.parts) > 1 else "public"
    if first_part in {"employee", "hr", "internal"}:
        return "internal"
    return first_part if first_part in VISIBILITIES else "public"

# RAG（检索增强生成）系统中最核心的数据预处理流水线
def _metadata(path: Path, docs_dir: Path, **extra) -> dict:
    return {
        "source": path.name,
        "source_path": path.relative_to(docs_dir).as_posix(),
        "visibility": _visibility(path, docs_dir),
        "file_type": path.suffix.lower().lstrip("."),
        **extra,
    }

# [新增] 计算文件内容的 MD5 哈希值
def _compute_md5(file_path: Path) -> str:
    """计算文件的 MD5 值，用于内容去重"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"[警告] 无法读取文件哈希: {file_path}, 错误: {e}")
        return ""

def load_pdf(path: Path, docs_dir: Path) -> list[Document]:
    reader = PdfReader(str(path))
    documents: list[Document] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            documents.append(
                Document(
                    page_content=text,
                    metadata=_metadata(path, docs_dir, page=page_number),
                )
            )
    return documents

def load_docx(path: Path, docs_dir: Path) -> list[Document]:
    document = docx.Document(str(path))
    blocks = [paragraph.text.strip() for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            blocks.append(" | ".join(cell.text.strip() for cell in row.cells))
    text = "\n".join(block for block in blocks if block)
    if not text:
        return []
    return [Document(page_content=text, metadata=_metadata(path, docs_dir))]

def load_text(path: Path, docs_dir: Path) -> list[Document]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []
    return [Document(page_content=text, metadata=_metadata(path, docs_dir))]

# 单文件读取引擎
def load_file(path: Path, docs_dir: Path) -> list[Document]:
    # 提取文件后缀（.suffix）
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path, docs_dir)
    if suffix == ".docx":
        return load_docx(path, docs_dir)
    if suffix in {".txt", ".md"}:
        return load_text(path, docs_dir)
    raise ValueError("只支持 txt、md、pdf、docx")

# 全量目录加载器 增加去重逻辑
def load_docs(dir_path: str | Path | None = None) -> list[Document]:
    docs_dir = Path(dir_path or settings.docs_dir).resolve()
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"知识文档目录不存在：{docs_dir}")

    legacy_docs = sorted(docs_dir.rglob("*.doc"))
    if legacy_docs:
        names = "、".join(path.name for path in legacy_docs)
        raise ValueError(f"不支持旧版 .doc，请先转换为 .docx：{names}")

    documents: list[Document] = []

    seen_hashes = set()  # [新增] 用于记录已处理文件的 MD5 值
    duplicate_count = 0  # [新增] 统计跳过的重复文件数

    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        # [新增] 内容去重校验
        file_hash = _compute_md5(path)
        if file_hash in seen_hashes:
            print(f"[跳过重复文件] {path.name} (内容与已加载文件相同)")
            duplicate_count += 1
            continue

        documents.extend(load_file(path, docs_dir))
    if duplicate_count > 0:
        print(f"[入库完成] 共跳过 {duplicate_count} 个重复文件。")
    return documents

# 文本切块器（Chunking）
def split_docs(documents: list[Document]) -> list[Document]:
    # 递归字符分割器
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        add_start_index=True,
    )
    return splitter.split_documents(documents)
