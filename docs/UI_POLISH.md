# DocIntel UI Polish — Release Candidate

Portfolio-ready frontend refactor. No backend or AI logic changes.

## Before vs After

| Area | Before | After |
|------|--------|-------|
| Layout | Two-column: upload sidebar + chat | Single-column, chat-first |
| Upload | Large persistent ingestion card + doc list | Centered upload when empty; compact summary after index |
| Task modes | Small cards with descriptions | Prominent tab bar (Q&A / Summarize / Anomalies) |
| Architecture | Full section on homepage | Moved to `/architecture` only |
| Debug | Visible checkbox under tasks | Collapsed **Advanced settings** |
| Stats | Three stat cards incl. document ID | Inline pages/chunks in summary bar |
| Visual density | Multiple elevated cards competing | Light background, one primary surface for answers |
| Demo / screenshots | All metadata visible | **Demo mode** hides debug, sources detail, IDs |

## Primary workflow (homepage)

```
Upload Document → Select Mode → Ask Question → View Answer
```

## Components removed from homepage

- `ArchitectureSection` (deleted)
- `Features` section (removed from `DocIntelApp`)
- `Hero` marketing block when document loaded (removed)
- `UploadPanel` sidebar layout (replaced by `UploadZone` + `DocumentSummary`)
- `DocumentStats` grid (replaced by compact summary)

## Components moved to secondary views

| Component | Location |
|-----------|----------|
| `ArchitectureDiagram` | `/architecture` |
| Retrieval debug / internals | **Advanced settings** (collapsed) |
| Feature marketing grid | Removed from main flow (can re-add to `/about` later) |

## New components

- `UploadZone` — focused empty-state upload
- `DocumentSummary` — compact indexed document header + replace
- `AdvancedSettings` — collapsible debug toggle
- `UIContext` — portfolio / demo mode state

## Portfolio screenshot mode

Toggle **Demo mode** in the header (camera icon).

When enabled:

- Hides advanced settings
- Hides retrieval debug, confidence badges, source excerpts, grounding panels
- Shows minimal “N sources cited” under answers
- Disables debug API flag on chat requests

### Recommended screenshots

1. **Empty state** — centered upload, workflow steps, clean headline  
   `npm run dev` → http://localhost:3000 (no document)

2. **Active Q&A** — enable Demo mode, ask a strong technical question, capture answer area  
   Crop: document summary + tabs + answer (hide browser chrome)

3. **Mode selection** — capture tab bar with Q&A selected before typing

4. **Architecture** — http://localhost:3000/architecture with **Play flow** running  
   Good for README / LinkedIn “how it works” posts

### Tips

- Use 1440×900 or 1280×800 viewport
- Light mode only (`#FAFAFA` background)
- Prefer one indexed manual (e.g. Intel SDM) for credible demo answers
- Record LinkedIn clips with Demo mode on and slow scroll through a long answer

## Run locally

```bash
cd frontend && npm run dev
```

Open http://localhost:3000
