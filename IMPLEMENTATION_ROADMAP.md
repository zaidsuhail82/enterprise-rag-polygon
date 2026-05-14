# Enterprise RAG System - Implementation Roadmap

**Project:** Executive Knowledge Platform with Explainable AI  
**Architecture:** Dual-pattern RAG with Blame Attribution Pipeline  
**Status:** Phase 0 → Phase 1  

---

## 🎯 **Project Goals**

Build an enterprise-grade RAG system that serves two distinct query patterns:

1. **Activity Monitoring** (Pattern A)  
   - "What has my CTO been working on this week?"
   - Requires: recency weighting, author metadata, Drive activity signals

2. **Institutional Memory** (Pattern B)  
   - "What work have we done in oil and gas sector?"
   - Requires: deep semantic search, sector tags, project aggregation

**Key Requirements:**
- ✅ Private deployment (no public URL) + globally accessible via Cloudflare Access
- ✅ Full explainability: citations, confidence scores, blame attribution
- ✅ RBAC from day one (permissive board-mode initially)
- ✅ Sub-3 second response latency (p95)
- ✅ Hallucination detection with NLI verification

---

## 📋 **Phase 0: Decisions & Access**

**Status:** ⏳ IN PROGRESS

### Critical Decisions (Must resolve before Phase 1)

- [ ] **D1 - Data Egress Policy**  
  Can document text reach OpenAI/Anthropic APIs?
  - [ ] YES → Use cloud LLMs (recommended: Claude 3.5 Haiku/Sonnet)
  - [x] NO → Use Ollama + Mistral (self-hosted, slower, lower quality)
  - [ ] **Action:** Get written confirmation from CEO/CTO
  
- [ ] **D2 - Deployment Host**  
  - [ ] Option A: Their own VPS/server (zero hosting cost, they own ops)
  - [x] Option B: Cloud hosting (Fly.io/Railway, ~$20-50/month, easier ops)
  - [ ] **Action:** Confirm with CTO
  
- [ ] **D3 - Google Workspace Tier**  
  - [ ] Enterprise tier? (unlocks Audit Log API, DLP, Admin SDK)
  - [x] Standard/Business tier?
  - [ ] **Action:** Ask CTO to confirm current tier
  
- [ ] **D4 - Hallucination Detection Method**  
  - [x] Option A: NLI model (DeBERTa) - free, ~200ms latency (RECOMMENDED for Phase 1)
  - [ ] Option B: Second LLM pass - higher accuracy, ~500ms latency, API cost
  - [ ] Option C: Hybrid (NLI first, LLM for borderline cases)
  
- [ ] **D5 - Incremental Sync Frequency**  
  - [ ] Near real-time (Push Notifications, requires Workspace Business+)
  - [x] 15-minute scheduled sync (works on all tiers)
  - [ ] **Action:** Based on Workspace tier, set initial frequency

### Access Setup

- [ ] **Google Workspace Service Account**  
  - [ ] Created service account in GCP Console
  - [ ] Downloaded JSON key to `secrets/service_account.json`
  - [ ] Enabled Google Drive API
  - [ ] Domain-wide delegation configured (if using admin scopes)
  - [ ] Service account has read access to target Drive folder
  
- [ ] **Supabase Account**  
  - [ ] Created project at supabase.com
  - [ ] Copied `SUPABASE_URL` to `.env`
  - [ ] Copied `SUPABASE_SERVICE_KEY` (service_role key) to `.env`
  - [ ] Google OAuth configured for auth
  
- [ ] **GitHub Repository**  
  - [ ] Repo initialized with scaffold
  - [ ] `.env` added to `.gitignore`
  - [ ] `secrets/` added to `.gitignore`

### Environment Validation

Run the validator script:
```bash
python phase0_validator.py
```

**All checks must pass before proceeding to Phase 1.**

### Phase 0 Completion Gate

✅ **Exit Criteria:**
- All 5 critical decisions resolved and documented
- Service account active and verified
- `.env` fully configured
- Docker services (Qdrant, Ollama if needed) running
- Validation script passes all required checks

---

## 📋 **Phase 1: Secure Ingestion Pipeline**

**Goal:** Ingest entire Google Drive corpus with full metadata preservation

### 1.1 Google Drive Connector

- [ ] **Drive API Integration**
  ```python
  # backend/app/ingestion/drive_connector.py
  ```
  - [ ] Authenticate with service account
  - [ ] List files recursively from root folder
  - [ ] Fetch file metadata (author, modified date, folder path)
  - [ ] Handle pagination for large folders
  - [ ] Implement rate limiting (1000 req/100s Drive API limit)
  
- [ ] **Incremental Sync Logic**
  ```python
  # backend/app/ingestion/incremental_sync.py
  ```
  - [ ] Track last sync timestamp in database
  - [ ] Use Drive Changes API to detect modifications
  - [ ] Handle three cases: new files, edited files, deleted files
  - [ ] Store sync state in `ingestion_runs` table

### 1.2 Document Parsers

- [ ] **Google Docs Parser**
  - [ ] Export as plain text via Drive API
  - [ ] Preserve formatting metadata (headers, lists)
  - [ ] Extract inline images as separate assets
  
- [ ] **PDF Parser**
  ```bash
  pip install pdfplumber
  ```
  - [ ] Text extraction with layout awareness
  - [ ] Table detection and extraction
  - [ ] Handle scanned PDFs (OCR if needed via Tesseract)
  
- [ ] **Google Sheets Parser**
  - [ ] Export sheets as CSV
  - [ ] Row-aware chunking (preserve row context)
  - [ ] Include sheet name in metadata
  
- [ ] **PowerPoint Parser**
  ```bash
  pip install python-pptx
  ```
  - [ ] Extract text from slides
  - [ ] Preserve slide numbers
  - [ ] Extract speaker notes

### 1.3 Metadata Extraction & Enrichment

- [ ] **Author & Recency Metadata**
  - [ ] Extract `last_modified_by` email from Drive API
  - [ ] Parse `modified_time` as datetime
  - [ ] Store in chunk metadata for Pattern A queries
  
- [ ] **Folder Hierarchy**
  - [ ] Parse full folder path (e.g., `/Projects/Oil & Gas/Shell 2023`)
  - [ ] Store as `folder_path` metadata
  - [ ] Extract project name from top-level folder
  
- [ ] **Sector Tags** (Phase 1 - simple keyword matching)
  - [ ] Keyword lists for sectors: `['oil', 'gas', 'petroleum']` → 'Energy'
  - [ ] Apply tags based on folder name + document content
  - [ ] Store as array: `sector_tags: ['Energy', 'Infrastructure']`
  - [ ] **Phase 2:** Replace with LLM-based entity extraction

### 1.4 Chunking Strategy

- [ ] **Type-Aware Chunking**
  ```python
  # backend/app/ingestion/chunker.py
  ```
  - [ ] Google Docs: 512 tokens, 50 token overlap
  - [ ] PDFs: 400 tokens, 100 token overlap (more context for layout)
  - [ ] Sheets: Row-aware (no mid-row splits)
  - [ ] PowerPoint: Slide-aware (one chunk per slide or per paragraph)
  
- [ ] **Metadata Preservation**
  - [ ] Each chunk carries: `document_id`, `folder_path`, `author_email`, `modified_date`, `sector_tags`, `chunk_index`
  - [ ] Store in Qdrant payload

### 1.5 Embedding Pipeline

- [ ] **Embedding Model Selection**
  - [ ] Phase 1: `text-embedding-3-small` (OpenAI, $0.02/1M tokens)
  - [ ] Alternative: `nomic-embed-text` (self-hosted via Ollama if data egress = NO)
  
- [ ] **Batch Processing**
  - [ ] Batch embed 100 chunks at a time
  - [ ] Retry logic for API failures
  - [ ] Progress tracking in database
  
- [ ] **Vector Store Upsert**
  ```python
  # backend/app/ingestion/vector_store.py
  ```
  - [ ] Create Qdrant collection with metadata schema
  - [ ] Upsert chunks with embeddings + metadata
  - [ ] Create indexes on: `author_email`, `modified_date`, `folder_path`, `sector_tags`

### 1.6 Database Schema Setup

Run migrations to create:

- [ ] **`documents` table**
  ```sql
  CREATE TABLE documents (
    id UUID PRIMARY KEY,
    drive_file_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    folder_path TEXT,
    owner_email TEXT,
    last_modified TIMESTAMP,
    last_modified_by_email TEXT,
    sector_tags TEXT[],
    doc_type TEXT,
    indexed_at TIMESTAMP,
    chunk_count INTEGER
  );
  ```

- [ ] **`ingestion_runs` table**
  ```sql
  CREATE TABLE ingestion_runs (
    id UUID PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT, -- 'running', 'completed', 'failed'
    files_processed INTEGER,
    chunks_created INTEGER,
    errors JSONB
  );
  ```

### 1.7 CLI Testing

- [ ] **Initial Ingestion Script**
  ```bash
  python scripts/initial_ingest.py --folder-id <DRIVE_FOLDER_ID>
  ```
  - [ ] Lists all files in Drive folder
  - [ ] Parses and chunks documents
  - [ ] Embeds and stores in Qdrant
  - [ ] Logs progress to database
  
- [ ] **Verification Queries**
  ```bash
  python scripts/verify_ingestion.py
  ```
  - [ ] Count documents in database
  - [ ] Count chunks in Qdrant
  - [ ] Sample random chunks and verify metadata
  - [ ] Check for missing files

### Phase 1 Completion Gate

✅ **Exit Criteria:**
- [ ] 100% of Drive corpus indexed
- [ ] All metadata fields populated correctly
- [ ] Incremental sync tested (add/edit/delete a test file)
- [ ] No errors in ingestion logs
- [ ] Database and Qdrant counts match expected

**Validation Command:**
```bash
python scripts/phase1_validation.py
```

---

## 📋 **Phase 2: Retrieval & Generation Pipeline**

**Goal:** Build query → answer pipeline with explainability

### 2.1 Query Classifier

- [ ] **Intent Detection**
  ```python
  # backend/app/retrieval/query_classifier.py
  ```
  - [ ] Rule-based classifier (Phase 1):
    - Pattern A signals: "working on", "recently", "this week", person names
    - Pattern B signals: sector names, "prior work", "projects", "done for"
  - [ ] Returns: `QueryPattern.ACTIVITY_MONITORING` or `QueryPattern.INSTITUTIONAL_MEMORY`
  
- [ ] **Route to Retrieval Strategy**
  - [ ] Pattern A → metadata-heavy retrieval (recency + author filters)
  - [ ] Pattern B → semantic-heavy retrieval (vector similarity + sector tags)

### 2.2 Hybrid Retriever

- [ ] **Semantic Search (Vector)**
  ```python
  # backend/app/retrieval/semantic_retriever.py
  ```
  - [ ] Query embedding via same model as documents
  - [ ] Cosine similarity search in Qdrant
  - [ ] Return top-20 candidates
  
- [ ] **Sparse Search (BM25)**
  ```python
  # backend/app/retrieval/bm25_retriever.py
  ```
  - [ ] Index document chunks with BM25
  - [ ] Keyword search for exact matches (client names, project codes)
  - [ ] Return top-20 candidates
  
- [ ] **Fusion**
  ```python
  # backend/app/retrieval/hybrid_retriever.py
  ```
  - [ ] Reciprocal Rank Fusion (RRF) to combine scores
  - [ ] Merge results, remove duplicates
  - [ ] Return top-20 for re-ranking

### 2.3 Metadata Filtering (Pattern-Specific)

- [ ] **Pattern A Filters**
  - [ ] `author_email` filter (if person name in query → resolve to email)
  - [ ] `modified_date` recency weighting (boost recent documents)
  - [ ] Time range filter: last 7 days, 30 days, 90 days based on query
  
- [ ] **Pattern B Filters**
  - [ ] `sector_tags` filter (if sector mentioned in query)
  - [ ] `folder_path` filter (if project name mentioned)
  - [ ] No recency weighting (historical work is equally relevant)

### 2.4 Re-Ranker

- [ ] **Cross-Encoder Re-Ranking**
  ```bash
  pip install sentence-transformers
  ```
  - [ ] Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
  - [ ] Re-rank top-20 candidates to top-5
  - [ ] Significant precision improvement
  
- [ ] **RBAC Filter** (permissive mode for Phase 1)
  - [ ] Check user role permissions against chunk metadata
  - [ ] Board role → all chunks pass
  - [ ] Future: implement granular folder/document restrictions

### 2.5 Grounded Generator

- [ ] **LLM Integration**
  ```python
  # backend/app/generation/generator.py
  ```
  - [ ] Model: Claude 3.5 Haiku (speed) or Sonnet (quality)
  - [ ] System prompt: "Answer ONLY using the provided context. Do not extrapolate."
  - [ ] Context window: top-5 chunks + metadata
  
- [ ] **Structured Output**
  ```json
  {
    "answer": "The CTO has been working on...",
    "supporting_chunks": [
      {"chunk_id": "...", "document_name": "...", "snippet": "..."}
    ],
    "confidence_score": 0.85
  }
  ```

### 2.6 Hallucination Detector (NLI)

- [ ] **NLI Model Setup**
  ```bash
  pip install transformers torch
  ```
  - [ ] Model: `microsoft/deberta-v3-base-mnli-fever-anli`
  - [ ] Load once at startup, run inference in-process
  
- [ ] **Claim Verification**
  ```python
  # backend/app/verification/nli_verifier.py
  ```
  - [ ] Extract claims from generated answer (sentence-level)
  - [ ] Score each claim against retrieved chunks
  - [ ] Entailment threshold: 0.7 (tune based on testing)
  - [ ] Output: `{supported_claims[], flagged_claims[], faithfulness_score}`
  
- [ ] **Threshold Logic**
  - [ ] Faithfulness score < 0.6 → return "Low confidence answer, verify sources"
  - [ ] 0.6-0.8 → return answer with warning
  - [ ] >0.8 → return answer with high confidence

### 2.7 Blame Attributor

- [ ] **Failure Classification**
  ```python
  # backend/app/verification/blame_attributor.py
  ```
  - [ ] **Retriever Blame:** Relevant documents not in top-K
    - Test: Run expanded retrieval (top-50), check if answer improves
    - If yes → retriever failed to surface relevant docs
  - [ ] **Generator Blame:** Documents retrieved but answer unsupported
    - Test: Check NLI scores per chunk
    - If chunks support the claim but answer doesn't cite them → generator hallucinated
  
- [ ] **Output**
  ```json
  {
    "blame_type": "retriever" | "generator" | "none",
    "diagnosis": "Relevant documents exist but ranked too low",
    "suggested_fix": "Tune BM25 weights for project name queries"
  }
  ```

### 2.8 Explainability Formatter

- [ ] **Response Assembly**
  ```python
  # backend/app/api/response_formatter.py
  ```
  - [ ] Combine: answer text, citations, faithfulness score, blame (if any)
  - [ ] Format citations with document links (Drive URLs)
  - [ ] Include chunk snippets (100 chars before/after match)
  
- [ ] **Example Output**
  ```
  **Answer:**
  The CTO has been working on the Japan deal, specifically finalizing the contract terms with Mitsubishi Heavy Industries.
  
  **Sources:**
  1. "Japan Deal - Contract Terms.docx" (modified Mar 15, 2025 by cto@company.com)
     → "...finalizing contract terms with MHI regarding the offshore wind project..."
     
  2. "Weekly Status Report - Mar 10.pdf"
     → "...CTO in Tokyo this week for final negotiations..."
  
  **Confidence:** High (92%)
  ```

### 2.9 API Endpoints

- [ ] **POST /query**
  ```python
  # backend/app/api/routes/query.py
  ```
  - [ ] Input: `{query: str, user_id: str}`
  - [ ] Pipeline: classifier → retriever → re-ranker → generator → NLI → blame → formatter
  - [ ] Output: `{answer, citations, confidence, blame_attribution?}`
  - [ ] Log to audit_log table
  
- [ ] **GET /query/{query_id}**
  - [ ] Retrieve past query result from audit log
  
- [ ] **GET /health**
  - [ ] Check all pipeline components: Qdrant, Supabase, LLM API, NLI model
  - [ ] Return: `{status: 'healthy' | 'degraded', components: {...}}`

### Phase 2 Completion Gate

✅ **Exit Criteria:**
- [ ] Pattern A query accuracy >80% on test set (CTO activity queries)
- [ ] Pattern B query accuracy >80% on test set (institutional memory)
- [ ] Hallucination detection rate >90% (NLI catches unsupported claims)
- [ ] Blame attribution correctly classifies failures in >80% of low-confidence cases
- [ ] All API endpoints testable via Postman/curl

**Validation:**
```bash
python tests/test_query_pipeline.py
```

---

## 📋 **Phase 3: Private Web Application**

**Goal:** Deploy executive-grade UI with Cloudflare Access

### 3.1 Frontend Development

- [ ] **React + TypeScript Setup**
  ```bash
  cd frontend
  npm install
  npm run dev
  ```
  
- [ ] **Query Interface**
  ```tsx
  // frontend/src/components/QueryInterface.tsx
  ```
  - [ ] Search bar with auto-focus
  - [ ] Loading state with skeleton
  - [ ] Real-time streaming (if supported)
  
- [ ] **Citations Display**
  ```tsx
  // frontend/src/components/CitationCard.tsx
  ```
  - [ ] Document name + Drive link
  - [ ] Snippet with highlighting
  - [ ] Confidence badge
  - [ ] Inline, not hidden behind toggle
  
- [ ] **Blame Attribution UI**
  ```tsx
  // frontend/src/components/BlameAlert.tsx
  ```
  - [ ] Only shown for low-confidence answers
  - [ ] Clear explanation: "The system struggled to find relevant documents" vs "The system found documents but couldn't generate a confident answer"
  - [ ] Actionable for admins: "Consider adding more project documentation"

### 3.2 Authentication

- [ ] **Supabase Auth Integration**
  ```typescript
  // frontend/src/lib/supabase.ts
  ```
  - [ ] Google SSO via Supabase Auth
  - [ ] Store JWT in localStorage
  - [ ] Attach to all API requests
  
- [ ] **User Session Management**
  - [ ] Redirect unauthenticated users to login
  - [ ] Fetch user role from database
  - [ ] Display current user in navbar

### 3.3 Cloudflare Access Setup

- [ ] **Create Cloudflare Account**
  - [ ] Sign up at cloudflare.com
  - [ ] Enable Zero Trust (free tier)
  
- [ ] **Configure Access Application**
  - [ ] Add application pointing to your backend URL
  - [ ] Enable Google OAuth as identity provider
  - [ ] Create access policy: allow emails in `@company.com` domain
  - [ ] Copy `CLOUDFLARE_TEAM_DOMAIN` and `CLOUDFLARE_AUD` to `.env`
  
- [ ] **Test Access Flow**
  - [ ] Visit app URL unauthenticated → should redirect to Cloudflare login
  - [ ] Authenticate with Google → should redirect to app
  - [ ] JWT should be present in request headers

### 3.4 Admin Dashboard

- [ ] **Ingestion Status**
  ```tsx
  // frontend/src/pages/Admin.tsx
  ```
  - [ ] Last ingestion run timestamp
  - [ ] Files processed, chunks created
  - [ ] Errors (if any)
  - [ ] Trigger manual sync button
  
- [ ] **User Management** (Phase 1: view only)
  - [ ] List users with roles
  - [ ] Last active timestamp
  
- [ ] **Query Analytics**
  - [ ] Most frequent queries
  - [ ] Average confidence score
  - [ ] Blame attribution breakdown

### 3.5 Performance Optimization

- [ ] **Response Streaming**
  - [ ] Stream LLM tokens as they generate
  - [ ] Display partial answer while waiting for full response
  
- [ ] **Caching**
  - [ ] Cache repeated queries (Redis or in-memory)
  - [ ] TTL: 5 minutes for Pattern A (activity changes), 24 hours for Pattern B
  
- [ ] **Lazy Loading**
  - [ ] Load citations on expand
  - [ ] Paginate admin dashboard

### Phase 3 Completion Gate

✅ **Exit Criteria:**
- [ ] App inaccessible without Cloudflare Access authentication
- [ ] Board members successfully authenticate from multiple locations
- [ ] Query → answer latency p95 <3 seconds
- [ ] UI renders correctly on desktop + mobile
- [ ] All features functional: query, citations, admin dashboard

**Validation:**
```bash
# From different network (not localhost)
curl https://your-app-url.com
# Should return Cloudflare auth challenge, not app content
```

---

## 📋 **Phase 4: Hardening & Audit**

**Goal:** Production-ready security and monitoring

### 4.1 RBAC Implementation

- [ ] **Database Schema**
  - [ ] `users`, `roles`, `access_policies` tables created
  - [ ] Board role created with full access
  - [ ] Seed initial board members
  
- [ ] **ACL Enforcement**
  ```python
  # backend/app/core/rbac.py
  ```
  - [ ] Check user role on every query
  - [ ] Filter chunks based on `access_policies` (permissive for board)
  - [ ] Log access attempts

### 4.2 Audit Logging

- [ ] **Comprehensive Logging**
  ```sql
  CREATE TABLE audit_log (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    query TEXT NOT NULL,
    query_pattern TEXT, -- 'activity_monitoring' | 'institutional_memory'
    chunks_retrieved JSONB,
    answer TEXT,
    faithfulness_score FLOAT,
    blame_attribution JSONB,
    latency_ms INTEGER,
    timestamp TIMESTAMP DEFAULT NOW()
  );
  ```
  
- [ ] **Queryable Interface**
  - [ ] Admin can view full query history
  - [ ] Filter by user, date range, confidence score
  - [ ] Export to CSV

### 4.3 Security Review

- [ ] **No Unauthenticated Routes**
  - [ ] All API endpoints require valid JWT
  - [ ] Health check endpoint can be public or behind basic auth
  
- [ ] **No Raw Document Exposure**
  - [ ] API responses only include chunk snippets (not full document text)
  - [ ] Document downloads require separate Drive permissions
  
- [ ] **Secrets Management**
  - [ ] All secrets in `.env`, never in code
  - [ ] `.env` in `.gitignore`
  - [ ] Rotate service account keys every 90 days (calendar reminder)

### 4.4 Observability

- [ ] **Structured Logging**
  ```python
  import structlog
  logger = structlog.get_logger()
  logger.info("query_executed", query=query, user_id=user_id, latency_ms=latency)
  ```
  
- [ ] **Monitoring Alerts**
  - [ ] Latency >5s → alert
  - [ ] Faithfulness score <0.5 for >10% of queries → alert
  - [ ] Ingestion job failed → alert
  
- [ ] **Health Checks**
  - [ ] `/health` endpoint checks: Qdrant, Supabase, LLM API
  - [ ] Return 200 if all healthy, 503 if degraded

### Phase 4 Completion Gate

✅ **Exit Criteria:**
- [ ] Security checklist 100% complete
- [ ] Audit log reviewed and approved by CTO
- [ ] Zero unauthenticated routes verified
- [ ] Secrets rotated and stored securely
- [ ] Monitoring alerts tested and working

---

## 📋 **Phase 5: Production Deployment**

**Goal:** Live system with monitoring and handover

### 5.1 Deployment

- [ ] **Choose Hosting**
  - [ ] Fly.io private networking OR
  - [ ] Railway private service OR
  - [ ] Their own VPS
  
- [ ] **CI/CD Pipeline**
  ```yaml
  # .github/workflows/deploy.yml
  ```
  - [ ] Trigger on push to `main`
  - [ ] Run tests
  - [ ] Build Docker image
  - [ ] Deploy to production
  
- [ ] **Environment Variables**
  - [ ] Set all secrets in hosting platform's secret manager
  - [ ] Verify no `.env` committed to repo

### 5.2 Production Testing

- [ ] **Smoke Tests**
  - [ ] CEO runs 5 test queries
  - [ ] All queries return answers <3s
  - [ ] Citations accurate
  
- [ ] **Load Testing**
  ```bash
  ab -n 100 -c 10 https://your-app-url.com/query
  ```
  - [ ] 10 concurrent users
  - [ ] p95 latency <3s
  - [ ] No errors

### 5.3 Documentation

- [ ] **Runbook**
  - [ ] How to trigger manual ingestion
  - [ ] How to add new users
  - [ ] How to rotate service account key
  - [ ] How to investigate low-confidence queries
  
- [ ] **Admin Training**
  - [ ] Walk CTO through admin dashboard
  - [ ] Show how to view audit logs
  - [ ] Explain blame attribution

### 5.4 Monitoring Setup

- [ ] **Alerts Configured**
  - [ ] Email/Slack for critical errors
  - [ ] Daily digest of query stats
  
- [ ] **Dashboard Access**
  - [ ] CTO has admin access
  - [ ] You have read access for support

### Phase 5 Completion Gate

✅ **Exit Criteria:**
- [ ] First live queries from CEO and board members
- [ ] Monitoring alerts firing correctly
- [ ] CTO has full admin access
- [ ] Documentation complete
- [ ] Handover meeting held

---

## 📋 **Phase 6: RBAC Expansion & Agents** (Future)

**Goal:** Multi-tier access and automation

### 6.1 RBAC Phase 2

- [ ] Add team-level roles (`team_lead`, `department_member`)
- [ ] Folder-level access policies
- [ ] Document-level access policies
- [ ] Test permission isolation

### 6.2 Advanced Features

- [ ] **Slack Bot Interface**
  - [ ] `/query` command
  - [ ] Direct messages to bot
  
- [ ] **Workflow Agents**
  - [ ] Deal prep: "Generate briefing for [client]"
  - [ ] Sector report: "Summarize all oil & gas projects"

---

## 🚀 **Current Status: Phase 0 → Phase 1**

**Next Actions:**

1. Run `python phase0_validator.py` to verify setup
2. Resolve 5 critical decisions (D1-D5)
3. Complete corpus preparation (Google Drive folder ready)
4. Begin Phase 1: Initial ingestion

**Questions for CTO:**
- Data egress policy (D1)
- Deployment host preference (D2)
- Google Workspace tier (D3)
- Hardware availability for self-hosted LLM (relates to D1)

Once Phase 0 validation passes, we're ready to ingest. 🎯
