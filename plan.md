# InvestiGator Backend Architecture Plan (Django)

## 1. Project Structure

```
investigator_backend/
├── investigator/                      # Main project config
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── investigations/          # Core investigation logic
│   ├── agents/                  # Agent orchestration
│   ├── entities/                # Entity & relationship management
│   ├── evidence/                # Evidence tracking
│   ├── board/                   # Investigation board data
│   ├── voice/                   # Gemini Live API integration
│   ├── reports/                 # Report generation
│   └── users/                   # User management
├── core/
│   ├── gemini_client.py        # Gemini API wrapper
│   ├── websocket_handler.py    # Real-time updates
│   └── celery_tasks.py         # Background jobs
└── manage.py
```

---

## 2. Database Models

### 2.1 Users App

**Model: User (extends AbstractUser)**

```python
- id (UUID)
- email (unique)
- full_name
- avatar_url
- subscription_tier (free/pro/enterprise)
- api_quota_remaining
- created_at
- last_login
```

---

### 2.2 Investigations App

**Model: Investigation**

```python
- id (UUID, primary key)
- user (FK → User)
- title (CharField, max_length=200)
- initial_query (TextField) # Original research question
- status (CharField: pending/running/paused/completed/failed)
- progress_percentage (IntegerField, 0-100)
- current_phase (CharField: planning/researching/analyzing/reporting)
- confidence_score (FloatField, 0-1)
- started_at (DateTimeField)
- completed_at (DateTimeField, null=True)
- estimated_completion (DateTimeField)
- total_api_calls (IntegerField)
- total_cost_usd (DecimalField)
- created_at
- updated_at
```

**Model: InvestigationPlan**

```python
- id (UUID)
- investigation (OneToOne → Investigation)
- research_strategy (JSONField) # List of planned steps
- hypothesis (TextField) # Current working hypothesis
- priority_areas (JSONField) # Areas to focus on
- avoided_paths (JSONField) # Dead ends to skip
- created_at
- updated_at
```

**Model: SubTask**

```python
- id (UUID)
- investigation (FK → Investigation)
- parent_task (FK → SubTask, null=True) # For nested tasks
- task_type (CharField: web_search/document_analysis/entity_extraction/relationship_mapping)
- description (TextField)
- status (CharField: pending/in_progress/completed/failed)
- result (JSONField, null=True)
- confidence (FloatField, 0-1)
- started_at
- completed_at
- order (IntegerField) # Execution order
```

---

### 2.3 Entities App

**Model: Entity**

```python
- id (UUID)
- investigation (FK → Investigation)
- entity_type (CharField: person/company/location/event/document/financial_instrument)
- name (CharField)
- aliases (JSONField) # List of alternative names
- description (TextField)
- confidence (FloatField, 0-1) # How sure agent is this entity is real
- source_count (IntegerField) # Number of sources mentioning this
- metadata (JSONField) # Type-specific data (DOB, registration number, etc.)
- position_x (FloatField, null=True) # For graph visualization
- position_y (FloatField, null=True)
- created_at
- discovered_by_task (FK → SubTask, null=True)
```

**Model: Relationship**

```python
- id (UUID)
- investigation (FK → Investigation)
- source_entity (FK → Entity)
- target_entity (FK → Entity)
- relationship_type (CharField: owns/works_for/connected_to/transacted_with/located_in/parent_of)
- description (TextField)
- confidence (FloatField, 0-1)
- start_date (DateField, null=True)
- end_date (DateField, null=True)
- is_active (BooleanField)
- strength (FloatField, 0-1) # Relationship strength for visualization
- created_at
- discovered_by_task (FK → SubTask, null=True)
```

---

### 2.4 Evidence App

**Model: Evidence**

```python
- id (UUID)
- investigation (FK → Investigation)
- evidence_type (CharField: document/web_page/image/video/testimony/financial_record)
- title (CharField)
- content (TextField) # Extracted/summarized content
- source_url (URLField, null=True)
- source_credibility (CharField: high/medium/low/unverified)
- file_path (FileField, null=True) # For uploaded documents
- file_type (CharField, null=True)
- metadata (JSONField) # Publication date, author, etc.
- created_at
- discovered_by_task (FK → SubTask, null=True)
```

**Model: EvidenceEntityLink**

```python
- id (UUID)
- evidence (FK → Evidence)
- entity (FK → Entity)
- relevance (CharField: primary/secondary/mentioned)
- quote (TextField, null=True) # Specific quote linking them
```

**Model: EvidenceRelationshipLink**

```python
- id (UUID)
- evidence (FK → Evidence)
- relationship (FK → Relationship)
- supports (BooleanField) # True if supports, False if contradicts
- strength (FloatField, 0-1) # How strongly it supports/contradicts
- quote (TextField, null=True)
```

---

### 2.5 Board App

**Model: InvestigationBoard**

```python
- id (UUID)
- investigation (OneToOne → Investigation)
- layout_type (CharField: force_directed/hierarchical/circular)
- viewport_settings (JSONField) # Zoom, pan position
- filter_settings (JSONField) # What's currently visible
- created_at
- updated_at
```

**Model: BoardAnnotation**

```python
- id (UUID)
- board (FK → InvestigationBoard)
- user (FK → User)
- annotation_type (CharField: note/highlight/question)
- content (TextField)
- position_x (FloatField)
- position_y (FloatField)
- linked_entity (FK → Entity, null=True)
- linked_relationship (FK → Relationship, null=True)
- created_at
```

---

### 2.6 Voice App

**Model: VoiceSession**

```python
- id (UUID)
- investigation (FK → Investigation)
- user (FK → User)
- status (CharField: active/paused/ended)
- started_at
- ended_at
- total_duration_seconds (IntegerField)
```

**Model: VoiceInteraction**

```python
- id (UUID)
- session (FK → VoiceSession)
- speaker (CharField: user/agent)
- transcript (TextField)
- audio_url (URLField, null=True)
- intent (CharField: question/redirect/confirmation/clarification)
- action_taken (CharField, null=True) # pause_investigation/change_focus/etc.
- timestamp
```

---

### 2.7 Reports App

**Model: Report**

```python
- id (UUID)
- investigation (FK → Investigation)
- report_type (CharField: executive_summary/full_report/entity_profile)
- title (CharField)
- content (TextField) # Markdown format
- format (CharField: markdown/pdf/html)
- file_path (FileField, null=True)
- generated_at
- version (IntegerField)
```

---

### 2.8 Agents App (Internal Agent State)

**Model: ThoughtChain**

```python
- id (UUID)
- investigation (FK → Investigation)
- sequence_number (IntegerField)
- thought_type (CharField: hypothesis/question/observation/conclusion/correction)
- content (TextField)
- parent_thought (FK → ThoughtChain, null=True)
- led_to_task (FK → SubTask, null=True)
- confidence_before (FloatField)
- confidence_after (FloatField)
- gemini_thought_signature (TextField, null=True) # For continuity
- timestamp
```

**Model: AgentDecision**

```python
- id (UUID)
- investigation (FK → Investigation)
- decision_point (TextField) # What decision was being made
- options_considered (JSONField) # List of options
- chosen_option (CharField)
- reasoning (TextField)
- outcome (CharField: successful/failed/abandoned, null=True)
- timestamp
```

---

## 3. API Endpoints

### 3.1 Authentication (`/api/auth/`)

```
POST   /register/                  # Register new user
POST   /login/                     # Login (JWT)
POST   /logout/                    # Logout
POST   /refresh-token/             # Refresh JWT
GET    /profile/                   # Get user profile
PATCH  /profile/                   # Update profile
```

---

### 3.2 Investigations (`/api/investigations/`)

```
POST   /                           # Create new investigation
GET    /                           # List user's investigations (paginated)
GET    /{id}/                      # Get investigation details
PATCH  /{id}/                      # Update investigation (pause/resume/cancel)
DELETE /{id}/                      # Delete investigation
GET    /{id}/status/               # Get real-time status
GET    /{id}/progress/             # Get progress details
POST   /{id}/redirect/             # Redirect agent focus (via voice or UI)
```

**POST / - Create Investigation**

```json
Request:
{
  "query": "Map the corporate ownership structure of TechCorp Inc",
  "focus_areas": ["ownership", "regulatory_filings", "board_members"],
  "depth_level": "comprehensive",  // shallow/moderate/comprehensive
  "time_range": {"start": "2020-01-01", "end": "2024-12-31"}
}

Response:
{
  "id": "uuid",
  "title": "TechCorp Inc Ownership Investigation",
  "status": "pending",
  "estimated_duration_minutes": 180,
  "created_at": "timestamp"
}
```

---

### 3.3 Entities (`/api/investigations/{inv_id}/entities/`)

```
GET    /                           # List all entities in investigation
GET    /{id}/                      # Get entity details
GET    /{id}/relationships/        # Get all relationships for entity
GET    /{id}/evidence/             # Get evidence mentioning entity
PATCH  /{id}/                      # Update entity (user corrections)
POST   /{id}/annotate/             # Add user note to entity
```

**GET / - List Entities**

```json
Response:
{
  "entities": [
    {
      "id": "uuid",
      "type": "company",
      "name": "TechCorp Inc",
      "confidence": 0.95,
      "source_count": 12,
      "metadata": {
        "registration_number": "12345",
        "jurisdiction": "Delaware",
        "founded": "2015"
      },
      "position": {"x": 100, "y": 200}
    }
  ],
  "count": 25
}
```

---

### 3.4 Relationships (`/api/investigations/{inv_id}/relationships/`)

```
GET    /                           # List all relationships
GET    /{id}/                      # Get relationship details
GET    /{id}/evidence/             # Get supporting/contradicting evidence
PATCH  /{id}/confidence/           # Update confidence (user override)
```

---

### 3.5 Evidence (`/api/investigations/{inv_id}/evidence/`)

```
GET    /                           # List all evidence
GET    /{id}/                      # Get evidence details with links
POST   /upload/                    # Upload document for analysis
GET    /{id}/content/              # Get full extracted content
```

**POST /upload/ - Upload Document**

```json
Request: multipart/form-data
{
  "file": <file>,
  "title": "2023 Annual Report",
  "source": "SEC.gov"
}

Response:
{
  "evidence_id": "uuid",
  "status": "processing",
  "estimated_analysis_time": 120
}
```

---

### 3.6 Board (`/api/investigations/{inv_id}/board/`)

```
GET    /                           # Get full board state (nodes + edges)
GET    /stream/                    # WebSocket: real-time board updates
PATCH  /layout/                    # Update layout settings
POST   /annotations/               # Create annotation
GET    /annotations/               # List annotations
DELETE /annotations/{id}/          # Delete annotation
POST   /filter/                    # Apply filters (show/hide entity types)
```

**GET / - Get Board State**

```json
Response:
{
  "nodes": [
    {
      "id": "entity-uuid",
      "type": "company",
      "label": "TechCorp Inc",
      "confidence": 0.95,
      "position": {"x": 100, "y": 200},
      "color": "#FF6B6B",
      "size": 30
    }
  ],
  "edges": [
    {
      "id": "relationship-uuid",
      "source": "entity-uuid-1",
      "target": "entity-uuid-2",
      "type": "owns",
      "label": "owns 75%",
      "confidence": 0.88,
      "style": "solid"  // solid/dashed based on confidence
    }
  ],
  "annotations": [...]
}
```

---

### 3.7 Voice (`/api/voice/`)

```
POST   /sessions/                  # Start voice session
POST   /sessions/{id}/end/         # End session
GET    /sessions/{id}/transcript/  # Get full transcript
POST   /stream/                    # WebSocket: bidirectional audio stream
```

**POST /sessions/ - Start Voice Session**

```json
Request:
{
  "investigation_id": "uuid"
}

Response:
{
  "session_id": "uuid",
  "websocket_url": "wss://api.investigator.com/voice/stream/{session_id}",
  "started_at": "timestamp"
}
```

---

### 3.8 Thoughts (`/api/investigations/{inv_id}/thoughts/`)

```
GET    /                           # Get thought chain timeline
GET    /stream/                    # WebSocket: real-time thought updates
GET    /decisions/                 # Get major decision points
```

**GET / - Thought Chain**

```json
Response:
{
  "thoughts": [
    {
      "id": "uuid",
      "sequence": 1,
      "type": "hypothesis",
      "content": "Initial hypothesis: TechCorp is majority owned by VentureX",
      "confidence_before": 0.3,
      "timestamp": "2024-01-29T10:00:00Z"
    },
    {
      "id": "uuid",
      "sequence": 2,
      "type": "observation",
      "content": "Found SEC filing showing VentureX owns only 15%",
      "led_to_task_id": "task-uuid",
      "timestamp": "2024-01-29T10:15:00Z"
    },
    {
      "id": "uuid",
      "sequence": 3,
      "type": "correction",
      "content": "Revised hypothesis: Ownership is distributed across multiple entities",
      "confidence_after": 0.7,
      "timestamp": "2024-01-29T10:20:00Z"
    }
  ]
}
```

---

### 3.9 Reports (`/api/investigations/{inv_id}/reports/`)

```
POST   /generate/                  # Generate report
GET    /                           # List available reports
GET    /{id}/                      # Get report content
GET    /{id}/download/             # Download as PDF
```

**POST /generate/ - Generate Report**

```json
Request:
{
  "report_type": "executive_summary",  // executive_summary/full_report/entity_profile
  "include_evidence": true,
  "include_confidence_scores": true,
  "target_entity_id": "uuid"  // Optional, for entity profiles
}

Response:
{
  "report_id": "uuid",
  "status": "generating",
  "estimated_completion_seconds": 45
}
```

---

### 3.10 Admin & Monitoring (`/api/admin/`)

```
GET    /stats/                     # System-wide statistics
GET    /investigations/active/     # List active investigations
GET    /api-usage/                 # Gemini API usage stats
GET    /costs/                     # Cost breakdown
```

---

## 4. WebSocket Connections

### 4.1 Investigation Updates

**Endpoint:** `ws://api.investigator.com/ws/investigations/{inv_id}/`

**Events from Server:**

```json
{
  "type": "status_update",
  "data": {
    "status": "running",
    "progress": 45,
    "current_phase": "analyzing"
  }
}

{
  "type": "entity_discovered",
  "data": {
    "entity": {...}
  }
}

{
  "type": "relationship_discovered",
  "data": {
    "relationship": {...}
  }
}

{
  "type": "thought_update",
  "data": {
    "thought": {...}
  }
}
```

**Events from Client:**

```json
{
  "type": "pause_investigation"
}

{
  "type": "redirect_focus",
  "data": {
    "focus": "Focus on 2023 financial transactions"
  }
}
```

---

### 4.2 Voice Stream

**Endpoint:** `ws://api.investigator.com/ws/voice/{session_id}/`

Uses WebRTC for bidirectional audio streaming with Gemini Live API.

---

## 5. Background Tasks (Celery)

### 5.1 Task Queue Setup

```python
CELERY_QUEUES = {
    'high_priority': {},      # Voice interactions
    'default': {},            # Investigation tasks
    'low_priority': {},       # Report generation
}
```

---

### 5.2 Core Tasks

**Task: `run_investigation`**

- Main orchestration task
- Monitors investigation lifecycle
- Handles failures and retries
- Updates progress in real-time

**Task: `execute_subtask`**

- Executes individual research subtasks
- Calls Gemini API with appropriate context
- Parses results and updates database
- Triggers entity/relationship extraction

**Task: `analyze_document`**

- Processes uploaded documents
- Extracts entities and relationships
- Links to evidence table
- Updates investigation board

**Task: `generate_report`**

- Compiles investigation data
- Uses Gemini to generate narrative
- Exports to PDF/Markdown
- Stores in cloud storage

**Task: `update_board_layout`**

- Recalculates entity positions
- Applies force-directed graph layout
- Optimizes for visualization
- Pushes updates via WebSocket

**Task: `cleanup_completed_investigations`**

- Archives old investigations
- Frees up resources
- Generates final reports

---

## 6. Gemini Integration Layer

### 6.1 Core Client (`core/gemini_client.py`)

```python
class GeminiClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = "gemini-3-marathon"  # For long-running agents

    def plan_investigation(self, query: str, context: dict) -> dict:
        """Generate investigation plan using Gemini 3"""
        # Returns: strategy, subtasks, estimated_duration

    def execute_research_step(self, subtask: SubTask, context: dict) -> dict:
        """Execute single research step with self-correction"""
        # Uses Thought Signatures for continuity
        # Returns: entities, relationships, evidence, confidence

    def extract_entities(self, text: str, context: dict) -> List[Entity]:
        """Extract entities from text"""

    def analyze_relationship(self, entity1: Entity, entity2: Entity, context: dict) -> Relationship:
        """Determine relationship between entities"""

    def evaluate_evidence(self, evidence: Evidence, claim: str) -> dict:
        """Assess evidence quality and relevance"""

    def generate_report(self, investigation: Investigation, report_type: str) -> str:
        """Generate narrative report"""

    def handle_voice_interaction(self, transcript: str, context: dict) -> dict:
        """Process voice input using Gemini Live API"""
```

---

### 6.2 Context Management

**Maintain full investigation context in Gemini's 1M token window:**

```python
def build_investigation_context(investigation: Investigation) -> dict:
    return {
        "query": investigation.initial_query,
        "plan": investigation.plan.research_strategy,
        "entities": serialize_entities(investigation),
        "relationships": serialize_relationships(investigation),
        "evidence": serialize_evidence(investigation),
        "thoughts": serialize_thought_chain(investigation),
        "current_phase": investigation.current_phase,
        "hypothesis": investigation.plan.hypothesis
    }
```

---

## 7. Middleware & Utilities

### 7.1 Custom Middleware

**RateLimitMiddleware**

- Enforce API rate limits per user tier
- Return 429 with retry-after header

**WebSocketAuthMiddleware**

- Authenticate WebSocket connections
- Validate JWT tokens

**LoggingMiddleware**

- Log all API calls with timing
- Track Gemini API usage

---

### 7.2 Permissions

```python
class InvestigationPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class QuotaPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.api_quota_remaining > 0
```

---

### 7.3 Serializers

**InvestigationSerializer**

- Full investigation details
- Include progress, entities count, status

**EntitySerializer**

- Entity with metadata
- Include relationships count

**BoardSerializer**

- Optimized for graph rendering
- Minimal payload size

---

## 8. Configuration & Settings

### 8.1 Environment Variables

```env
# Django
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=api.investigator.com

# Database
DATABASE_URL=postgresql://user:pass@localhost/investigator

# Gemini API
GEMINI_API_KEY=...
GEMINI_MODEL_DEFAULT=gemini-3-marathon
GEMINI_LIVE_API_ENABLED=True

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Storage
AWS_STORAGE_BUCKET_NAME=investigator-evidence
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# WebSocket
CHANNELS_REDIS_URL=redis://localhost:6379/1

# Limits
MAX_INVESTIGATION_DURATION_HOURS=24
MAX_ENTITIES_PER_INVESTIGATION=1000
MAX_CONCURRENT_INVESTIGATIONS_PER_USER=3
```

---

### 8.2 Django Apps

```python
INSTALLED_APPS = [
    # Django defaults
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
    'channels',
    'celery',
    'storages',

    # Project apps
    'apps.users',
    'apps.investigations',
    'apps.agents',
    'apps.entities',
    'apps.evidence',
    'apps.board',
    'apps.voice',
    'apps.reports',
]
```

---

## 9. Deployment Considerations

### 9.1 Infrastructure

**Application Server:**

- Gunicorn with multiple workers
- Nginx reverse proxy

**WebSocket Server:**

- Daphne (ASGI server for Channels)
- Redis for channel layer

**Background Workers:**

- Celery workers (3+ instances)
- Celery beat for scheduled tasks

**Database:**

- PostgreSQL with connection pooling
- Read replicas for heavy queries

**Cache:**

- Redis for session/cache
- Cache investigation context to reduce DB hits

**Storage:**

- AWS S3 for evidence files
- CloudFront CDN for report PDFs

---

### 9.2 Scaling Strategy

**Horizontal Scaling:**

- Load balancer for multiple app instances
- Queue partitioning for Celery workers
- Database sharding by user_id

**Performance Optimization:**

- Index on investigation.user_id, status
- Index on entity.investigation_id, entity_type
- Materialized view for board state
- Cache board JSON for 30 seconds
- Batch insert entities/relationships

---

## 10. Security Considerations

1. **API Authentication:**
   - JWT tokens with 1-hour expiry
   - Refresh tokens with 7-day expiry
   - Store refresh tokens in httpOnly cookies

2. **Input Validation:**
   - Sanitize user queries before passing to Gemini
   - Validate file uploads (type, size, content)
   - Rate limit investigation creation

3. **Data Privacy:**
   - Encrypt evidence files at rest
   - Anonymize logs
   - Allow users to delete investigations + cascade delete

4. **WebSocket Security:**
   - Validate JWT on connection
   - Limit message size and frequency
   - Auto-disconnect idle connections

5. **Gemini API:**
   - Never expose API keys to frontend
   - Implement request signing
   - Monitor for anomalous usage

---

## 11. Testing Strategy

### 11.1 Unit Tests

- Models: Entity creation, relationship validation
- Serializers: Data transformation
- Gemini client: Mock API responses

### 11.2 Integration Tests

- Full investigation flow
- WebSocket message handling
- Celery task execution

### 11.3 Load Tests

- 100 concurrent investigations
- WebSocket connection limits
- Database query performance

---

## 12. Monitoring & Logging

**Metrics to Track:**

- Investigation completion rate
- Average investigation duration
- Gemini API latency and errors
- Entity extraction accuracy (sample reviews)
- WebSocket connection count
- Celery queue depths

**Logging:**

- Structured JSON logs
- Log levels: DEBUG (dev), INFO (prod)
- Separate log files for: app, celery, websocket
- Log rotation every 24 hours

**Alerting:**

- Gemini API quota nearing limit
- Investigation stuck for >1 hour
- Celery worker failures
- Database connection pool exhausted

---

## 13. API Response Formats

### Success Response

```json
{
  "success": true,
  "data": {...},
  "meta": {
    "timestamp": "2024-01-29T12:00:00Z",
    "request_id": "uuid"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "INVALID_QUERY",
    "message": "Investigation query is too vague",
    "details": {...}
  },
  "meta": {
    "timestamp": "2024-01-29T12:00:00Z",
    "request_id": "uuid"
  }
}
```

---

## 14. Implementation Priority

### Phase 1 (Days 1-3): Core Foundation

- Set up Django project structure
- Implement User, Investigation, SubTask models
- Basic CRUD APIs for investigations
- Gemini client with plan_investigation() method

### Phase 2 (Days 4-6): Entity & Evidence System

- Implement Entity, Relationship, Evidence models
- Entity/relationship extraction from Gemini responses
- Evidence linking
- Database optimization (indexes, queries)

### Phase 3 (Days 7-9): Real-time & Board

- WebSocket setup with Channels
- Real-time investigation updates
- Board API with graph data
- Background task orchestration with Celery

### Phase 4 (Days 10-12): Advanced Features

- Voice session handling
- Thought chain visualization API
- Report generation
- Final integration and testing

---

## 15. Sample API Flow

**User creates investigation:**

1. `POST /api/investigations/` → Returns investigation_id
2. Backend creates Investigation in "pending" status
3. Celery task `run_investigation.delay(investigation_id)` is queued

**Background processing:** 4. Task calls `GeminiClient.plan_investigation()` 5. Creates SubTask objects from plan 6. For each subtask:

- Execute with `GeminiClient.execute_research_step()`
- Extract entities/relationships
- Save to database
- Push update via WebSocket

**Frontend receives real-time updates:** 7. WebSocket sends `entity_discovered` events 8. WebSocket sends `relationship_discovered` events 9. WebSocket sends `thought_update` events 10. Frontend updates board visualization

**User interacts:** 11. `POST /api/investigations/{id}/redirect/` with focus change 12. Agent adjusts research strategy 13. Continues with new focus

**Investigation completes:** 14. Status updates to "completed" 15. `POST /api/investigations/{id}/reports/generate/` 16. Report ready for download

---

## Notes

- All IDs are UUIDs for security (no enumeration attacks)
- Timestamps are UTC in ISO 8601 format
- Pagination uses cursor-based approach for performance
- All file uploads go through virus scanning
- Implement request/response compression (gzip)
- Use Django signals for audit logging
- Consider GraphQL for board queries (reduce over-fetching)
