"""向量检索服务。

负责问题向量化、租户及知识库过滤、pgvector 相似度排序。Embedding 实现通过
端口传入，因此本文件不依赖任何具体模型厂商。
"""

import uuid
import re
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_chunk import ChunkEmbedding, KnowledgeChunk
from app.ports.ai import EmbeddingProvider


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: KnowledgeChunk
    document: Document
    score: float


def retrieve_chunks(
    db: Session,
    *,
    embedding_provider: EmbeddingProvider,
    tenant_id: uuid.UUID,
    question: str,
    knowledge_base_ids: list[uuid.UUID],
    top_k: int,
) -> list[RetrievedChunk]:
    if not knowledge_base_ids:
        return []

    query_embedding = embedding_provider.embed_texts([question])[0]
    distance = ChunkEmbedding.embedding.cosine_distance(query_embedding).label("distance")
    statement = (
        select(KnowledgeChunk, Document, distance)
        .join(ChunkEmbedding, ChunkEmbedding.chunk_id == KnowledgeChunk.id)
        .join(Document, Document.id == KnowledgeChunk.document_id)
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeChunk.knowledge_base_id)
        .where(
            KnowledgeChunk.tenant_id == tenant_id,
            KnowledgeChunk.knowledge_base_id.in_(knowledge_base_ids),
            Document.status == "indexed",
            KnowledgeBase.status != "archived",
        )
        .order_by(distance)
        .limit(top_k)
    )
    rows = db.execute(statement).all()
    return [
        RetrievedChunk(chunk=chunk, document=document, score=max(0.0, 1.0 - float(distance_value)))
        for chunk, document, distance_value in rows
    ]


def retrieve_keyword_chunks(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    query: str,
    knowledge_base_ids: list[uuid.UUID],
    limit: int,
) -> list[RetrievedChunk]:
    """执行轻量关键词召回，弥补向量检索对专有名词和编号的漏召回。"""
    terms = _keyword_terms(query)
    if not knowledge_base_ids or not terms:
        return []
    keyword_filter = or_(*(KnowledgeChunk.content.ilike(f"%{term}%") for term in terms))
    statement = (
        select(KnowledgeChunk, Document)
        .join(Document, Document.id == KnowledgeChunk.document_id)
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeChunk.knowledge_base_id)
        .where(
            KnowledgeChunk.tenant_id == tenant_id,
            KnowledgeChunk.knowledge_base_id.in_(knowledge_base_ids),
            Document.status == "indexed",
            KnowledgeBase.status != "archived",
            keyword_filter,
        )
        .limit(limit)
    )
    rows = db.execute(statement).all()
    results: list[RetrievedChunk] = []
    for chunk, document in rows:
        content = chunk.content.lower()
        matched = sum(1 for term in terms if term.lower() in content)
        results.append(
            RetrievedChunk(
                chunk=chunk,
                document=document,
                score=min(1.0, matched / max(1, len(terms))),
            )
        )
    return sorted(results, key=lambda item: item.score, reverse=True)


def retrieve_hybrid_chunks(
    db: Session,
    *,
    embedding_provider: EmbeddingProvider,
    tenant_id: uuid.UUID,
    query: str,
    knowledge_base_ids: list[uuid.UUID],
    top_k: int,
) -> list[RetrievedChunk]:
    """融合向量和关键词结果，并按 chunk 去重后返回最终候选。"""
    candidate_limit = max(top_k, min(top_k * 2, 50))
    vector_results = retrieve_chunks(
        db,
        embedding_provider=embedding_provider,
        tenant_id=tenant_id,
        question=query,
        knowledge_base_ids=knowledge_base_ids,
        top_k=candidate_limit,
    )
    keyword_results = retrieve_keyword_chunks(
        db,
        tenant_id=tenant_id,
        query=query,
        knowledge_base_ids=knowledge_base_ids,
        limit=candidate_limit,
    )

    items: dict[uuid.UUID, RetrievedChunk] = {}
    scores: dict[uuid.UUID, float] = {}
    for rank, item in enumerate(vector_results, start=1):
        items[item.chunk.id] = item
        scores[item.chunk.id] = scores.get(item.chunk.id, 0.0) + 0.75 * item.score + 0.05 / rank
    for rank, item in enumerate(keyword_results, start=1):
        items[item.chunk.id] = item
        scores[item.chunk.id] = scores.get(item.chunk.id, 0.0) + 0.20 * item.score + 0.05 / rank

    ranked = sorted(items, key=lambda chunk_id: scores[chunk_id], reverse=True)[:top_k]
    return [
        RetrievedChunk(
            chunk=items[chunk_id].chunk,
            document=items[chunk_id].document,
            score=min(1.0, scores[chunk_id]),
        )
        for chunk_id in ranked
    ]


def _keyword_terms(query: str) -> list[str]:
    """提取英文单词、编号及有限数量的中文二元词，控制 SQL 条件规模。"""
    terms: list[str] = []
    for token in re.findall(r"[A-Za-z0-9_.-]{2,}|[\u4e00-\u9fff]{2,}", query):
        if re.fullmatch(r"[\u4e00-\u9fff]+", token) and len(token) > 4:
            terms.extend(token[index : index + 2] for index in range(min(len(token) - 1, 6)))
        else:
            terms.append(token)
    return list(dict.fromkeys(terms))[:8]
