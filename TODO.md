# Resume Ranker Debug & Fix TODO

## Phase 1: Root Cause Analysis ✅
- JD parser pulls markdown headers, locations, and entire sentences as "skills"
- Resume parser section bleed (missing LANGUAGE/ACTIVITIES headers)
- Resume parser extracts noise tokens like "proficient", "and mysql. strong grasp of" as skills
- Scorer gives 0 for missing projects, 20 for missing certs, 30 for missing edu
- No transferable skill matching (Flask ≠ FastAPI)
- Penalties up to 20 points destroy already-low scores
- Semantic similarity always 0 (embedding failures)

## Phase 2: Files to Fix
1. [ ] `backend/tools/jd_parser.py` — clean skill extraction, stop section bleed
2. [ ] `backend/tools/resume_parser.py` — fix section headers, skill noise filter, experience greediness
3. [ ] `backend/tools/scorer.py` — transferable skills, realistic defaults, fair weighting
4. [ ] `backend/tools/edge_handler.py` — reduce penalties, cap at 10
5. [ ] `backend/agents/jd_reader_agent.py` — validate/clean merged data
6. [ ] `backend/agents/ranking_agent.py` — add structured debug logging
7. [ ] `backend/agents/reasoning_agent.py` — filter garbage matched items
8. [ ] `backend/workflows/pipeline.py` — add pipeline-stage debug logs
9. [ ] Tests — update for new behavior
10. [ ] `run_debug_evaluation.py` — run on 3 real resumes, print rankings

## Phase 3: Execution In Progress

