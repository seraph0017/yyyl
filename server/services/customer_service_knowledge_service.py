"""
v1.8 智能客服知识库服务

回答策略必须保守：有可引用知识来源才回答；无来源、越权注入或敏感承诺类问题统一转人工。
"""

from __future__ import annotations

import html
import hmac
import hashlib
import re
import string
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree

from config import settings

ALLOWED_UPLOAD_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024
MIN_CONFIDENCE = 0.32

INJECTION_PATTERNS = (
    "忽略以上",
    "忽略前面",
    "忽略所有",
    "ignore previous",
    "system prompt",
    "后台密码",
    "管理员密码",
    "泄露",
    "token",
    "api key",
)

SENSITIVE_WITHOUT_SOURCE_PATTERNS = (
    "保证",
    "承诺",
    "最低价",
    "库存一定",
    "后台数据",
    "订单状态",
)


def validate_knowledge_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """归一化管理端手工维护的知识库 payload。"""
    title = str(payload.get("title") or "").strip()
    content = str(payload.get("content") or "").strip()
    if not title:
        raise ValueError("知识标题不能为空")
    if len(title) > 160:
        raise ValueError("知识标题不能超过160字")
    if not content:
        raise ValueError("知识正文不能为空")
    _reject_script_content(content)

    content_format = str(payload.get("content_format") or "markdown").strip()
    if content_format not in {"markdown", "text"}:
        raise ValueError("手工知识库仅支持 markdown/text 内容格式")

    source_type = str(payload.get("source_type") or "manual").strip()
    if source_type not in {"manual", "faq", "txt", "md", "pdf", "docx"}:
        raise ValueError("知识来源类型不支持")

    status = str(payload.get("status") or "draft").strip()
    if status not in {"draft", "published", "archived"}:
        raise ValueError("知识状态不支持")

    return {
        "title": title,
        "content": content,
        "content_format": content_format,
        "source_type": source_type,
        "source_name": (str(payload.get("source_name") or "").strip() or None),
        "keywords": normalize_keywords(payload.get("keywords")),
        "status": status,
    }


def normalize_keywords(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = re.split(r"[,，\s]+", value)
    elif isinstance(value, Iterable):
        raw = [str(item) for item in value]
    else:
        raw = []
    seen: set[str] = set()
    keywords: list[str] = []
    for item in raw:
        keyword = item.strip()
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        keywords.append(keyword[:32])
    return keywords[:20]


def validate_knowledge_upload(*, filename: str, size: int) -> None:
    """校验知识库上传文件，限制类型和大小，避免脚本类内容进入知识库。"""
    if not filename:
        raise ValueError("文件名不能为空")
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise ValueError("知识库文件仅支持 txt/md/pdf/docx")
    if size <= 0:
        raise ValueError("上传文件不能为空")
    if size > MAX_UPLOAD_SIZE:
        raise ValueError("知识库文件不能超过10MB")


async def read_upload_file_limited(
    file: Any,
    *,
    max_size: int = MAX_UPLOAD_SIZE,
    chunk_size: int = UPLOAD_CHUNK_SIZE,
) -> bytes:
    """分块读取上传文件，超过阈值立即中止，避免整包读入内存后才发现超限。"""
    content = bytearray()
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > max_size:
            raise ValueError("知识库文件不能超过10MB")
    return bytes(content)


def extract_text_from_knowledge_file(*, filename: str, content: bytes) -> tuple[str, str, str]:
    """从 txt/md/pdf/docx 中提取文本，返回 (text, content_format, source_type)。"""
    validate_knowledge_upload(filename=filename, size=len(content))
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        text = _decode_text(content)
        _reject_script_content(text)
        return text.strip(), "markdown" if suffix == ".md" else "text", suffix.lstrip(".")
    if suffix == ".docx":
        return _extract_docx_text(content), "text", "docx"
    if suffix == ".pdf":
        return _extract_pdf_text(content), "text", "pdf"
    raise ValueError("知识库文件类型不支持")


def select_knowledge_answer(
    *,
    question: str,
    articles: Iterable[Any],
    site_id: int,
) -> dict[str, Any]:
    """基于已发布知识库选择回答，拒绝无来源编造。"""
    normalized_question = normalize_question(question)
    if not normalized_question:
        return _human_answer(question, "请先输入要咨询的问题")
    if _looks_like_prompt_injection(normalized_question):
        return _human_answer(question, "这个问题需要人工客服确认")

    ranked: list[tuple[float, Any]] = []
    for article in articles:
        if getattr(article, "site_id", site_id) != site_id:
            continue
        if getattr(article, "status", "") != "published":
            continue
        score = _score_article(normalized_question, article)
        if score > 0:
            ranked.append((score, article))

    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] < MIN_CONFIDENCE:
        return _human_answer(question, "知识库暂未收录这个问题")

    score, best = ranked[0]
    answer = _build_answer(best)
    source = _build_source(best)
    return {
        "answer": answer,
        "sources": [source],
        "matched_article_ids": [best.id],
        "confidence": round(min(score, 1.0), 4),
        "needs_human": False,
    }


def build_ask_log_payload(
    *,
    site_id: int,
    channel: str,
    question: str,
    result: dict[str, Any],
    user_id: int | None = None,
    admin_id: int | None = None,
) -> dict[str, Any]:
    return {
        "site_id": site_id,
        "channel": channel,
        "user_id": user_id,
        "admin_id": admin_id,
        "question": question.strip(),
        "answer": result["answer"],
        "matched_article_ids": result.get("matched_article_ids") or [],
        "source_refs": result.get("sources") or [],
        "confidence": result.get("confidence") or 0,
        "needs_human": bool(result.get("needs_human")),
    }


def build_feedback_token(*, log_id: int, site_id: int, user_id: int | None) -> str:
    """生成绑定问答日志、营地和用户的反馈 token。"""
    payload = f"{log_id}:{site_id}:{user_id or 0}"
    digest = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{digest}"


def verify_feedback_token(
    token: str | None,
    *,
    log_id: int,
    site_id: int,
    user_id: int | None,
) -> bool:
    if not token:
        return False
    expected = build_feedback_token(log_id=log_id, site_id=site_id, user_id=user_id)
    return hmac.compare_digest(token, expected)


def serialize_article(article: Any) -> dict[str, Any]:
    return {
        "id": article.id,
        "site_id": article.site_id,
        "title": article.title,
        "content": article.content,
        "content_format": article.content_format,
        "source_type": article.source_type,
        "source_name": article.source_name,
        "keywords": article.keywords or [],
        "status": article.status,
        "published_at": article.published_at,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }


def serialize_ask_log(log: Any) -> dict[str, Any]:
    return {
        "id": log.id,
        "site_id": log.site_id,
        "channel": log.channel,
        "user_id": log.user_id,
        "admin_id": log.admin_id,
        "question": log.question,
        "answer": log.answer,
        "matched_article_ids": log.matched_article_ids or [],
        "source_refs": log.source_refs or [],
        "confidence": float(log.confidence or 0),
        "needs_human": log.needs_human,
        "feedback": log.feedback,
        "feedback_comment": log.feedback_comment,
        "created_at": log.created_at,
    }


def normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", str(question or "").strip())[:300]


def _score_article(question: str, article: Any) -> float:
    title = str(getattr(article, "title", "") or "")
    content = str(getattr(article, "content", "") or "")
    keywords = [str(item) for item in (getattr(article, "keywords", None) or [])]
    searchable = f"{title}\n{content}\n{' '.join(keywords)}"

    keyword_hits = sum(1 for keyword in keywords if keyword and keyword in question)
    char_hits = len(set(_chinese_bigrams(question)) & set(_chinese_bigrams(searchable)))
    direct_hits = sum(1 for token in _mixed_tokens(question) if token and token in searchable)
    if keyword_hits == 0 and char_hits == 0 and direct_hits == 0:
        return 0

    score = keyword_hits * 0.30 + min(char_hits, 6) * 0.11 + min(direct_hits, 5) * 0.09
    if _question_needs_system_confirmation(question) and score < 0.5:
        return 0
    return score


def _build_answer(article: Any) -> str:
    content = _strip_markdown(str(getattr(article, "content", "") or "")).strip()
    if len(content) <= 420:
        return content
    return f"{content[:420].rstrip()}..."


def _build_source(article: Any) -> dict[str, Any]:
    return {
        "id": article.id,
        "title": article.title,
        "source_type": article.source_type,
        "source_name": article.source_name,
    }


def _human_answer(question: str, reason: str) -> dict[str, Any]:
    return {
        "answer": f"{reason}，我已为你转到人工客服。涉及价格、库存、退款和订单状态时，请以工作人员确认为准。",
        "sources": [],
        "matched_article_ids": [],
        "confidence": 0,
        "needs_human": True,
    }


def _looks_like_prompt_injection(question: str) -> bool:
    lower = question.lower()
    return any(pattern in lower for pattern in INJECTION_PATTERNS)


def _question_needs_system_confirmation(question: str) -> bool:
    return any(pattern in question for pattern in SENSITIVE_WITHOUT_SOURCE_PATTERNS)


def _mixed_tokens(text: str) -> list[str]:
    cleaned = text.translate(str.maketrans("", "", string.punctuation))
    return [token for token in re.split(r"[\s，。！？、,.!?；;：:]+", cleaned) if len(token) >= 2]


def _chinese_bigrams(text: str) -> list[str]:
    chars = [char for char in text if "\u4e00" <= char <= "\u9fff"]
    return ["".join(chars[index:index + 2]) for index in range(max(len(chars) - 1, 0))]


def _strip_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"[#>*_`~-]+", "", text)
    return html.unescape(text)


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _reject_script_content(text: str) -> None:
    if re.search(r"<\s*script|javascript\s*:", text, flags=re.IGNORECASE):
        raise ValueError("知识库内容不允许包含脚本")


def _extract_docx_text(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            xml_data = archive.read("word/document.xml")
    except Exception as exc:
        raise ValueError("docx 文件解析失败") from exc

    root = ElementTree.fromstring(xml_data)
    texts: list[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            texts.append(node.text)
    text = "\n".join(texts).strip()
    if not text:
        raise ValueError("docx 文件没有可用文本")
    _reject_script_content(text)
    return text


def _extract_pdf_text(content: bytes) -> str:
    raw = _decode_text(content)
    pieces = re.findall(r"\(([^()]{2,})\)", raw)
    text = "\n".join(piece.replace(r"\)", ")").replace(r"\(", "(") for piece in pieces)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        # 兜底保留可读片段，避免解析依赖缺失时完全不可用。
        text = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9，。！？、,.!?；;：:\s-]", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 2:
        raise ValueError("pdf 文件没有可用文本")
    _reject_script_content(text)
    return text


def now_if_published(status: str) -> datetime | None:
    return datetime.now(timezone.utc) if status == "published" else None
