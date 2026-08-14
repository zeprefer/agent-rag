# Demo Enterprise Knowledge Policy

## Customer Support SLA

Demo Enterprise provides support for tenant administrators and end users through the enterprise help desk.

Critical incidents must receive an initial response within 30 minutes during business hours. A critical incident means that production knowledge search, document upload, or user question answering is unavailable for most users in a tenant.

High priority incidents must receive an initial response within 2 business hours. A high priority incident means that one important workflow is degraded but a workaround exists.

Normal questions must receive an initial response within 1 business day.

## Knowledge Base Governance

Only tenant administrators can create enterprise knowledge bases and upload official documents.

Every uploaded document is stored as an immutable document version. Re-uploading or replacing enterprise material must create a new version so that audit trails remain available.

Published knowledge bases can be used by tenant users in RAG chat sessions. Archived knowledge bases must not be selected for new chat sessions.

## Security Requirements

Confidential customer data must not be uploaded to public or personal knowledge bases.

Uploaded files must pass extension checks, content signature checks, and basic malware pattern scanning before they are stored.

User chat attachments are temporary session context. They can help answer the current question, but they must not be written into the official enterprise knowledge base.

## AI Answering Rules

The assistant should answer from retrieved enterprise knowledge first.

If retrieved context is insufficient, the assistant should say that the available knowledge base does not contain enough information.

When an answer uses enterprise knowledge, the assistant should return citations that include the source document title and relevant quote.
