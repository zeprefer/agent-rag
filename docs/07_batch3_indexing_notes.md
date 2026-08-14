# Batch 3: Document Parsing, Chunking, and Embedding Notes

## Runtime Flow

1. Admin uploads a document through the Batch 2 document API.
2. Admin calls `POST /api/v1/admin/documents/{document_id}/index`.
3. The backend reads the source file from object storage.
4. The parser extracts text from PDF, DOCX, DOC, or Markdown.
5. The chunker creates `knowledge_chunks` with page and heading metadata.
6. The Bailian/DashScope embedding provider generates vectors.
7. The backend writes `chunk_embeddings` to PostgreSQL + pgvector.
8. The document status becomes `indexed`, or `failed` with an error message.

## Required Environment

```env
DASHSCOPE_API_KEY=your-api-key
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
BAILIAN_EMBEDDING_MODEL=text-embedding-v4
BAILIAN_EMBEDDING_DIMENSIONS=1024
```

The vector column is currently fixed at 1024 dimensions. If the embedding dimension changes, create a new migration and rebuild existing embeddings.

## Implemented API

- `POST /api/v1/admin/documents/{document_id}/index`
- `GET /api/v1/admin/index-jobs`
- `GET /api/v1/admin/documents/{document_id}/chunks`

## Production Note

Batch 3 runs indexing synchronously to make the pipeline easy to verify. The next enterprise hardening step is moving `index_document` into Celery/RQ and using `document_processing_jobs` as the durable task state table.

