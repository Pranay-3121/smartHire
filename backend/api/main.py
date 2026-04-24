import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.core.config import settings
from backend.core.constants import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE_BYTES
from backend.core.logging import get_logger
from backend.schemas.api import (
    AnalyzeJobRequest, AnalyzeJobResponse,
    UploadResumesResponse, RankRequest, RankResponse,
    ResultsResponse, HealthResponse,
)
from backend.schemas.job import JobProfile
from backend.agents.jd_reader_agent import run_jd_reader_agent
from backend.workflows.pipeline import run_pipeline
from backend.services.storage import storage
from backend.services.ollama_client import ollama_client
from backend.services.embeddings import embedding_service
from backend.tools.exporter import export_to_csv, export_to_json, export_shortlist_report

logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered resume ranking and candidate evaluation platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory JD store per run
_jd_store: dict[str, str] = {}
_resume_store: dict[str, list[str]] = {}


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        ollama_connected=ollama_client.is_available(),
        chroma_connected=embedding_service.is_available(),
        version=settings.app_version,
    )


@app.post("/analyze-job", response_model=AnalyzeJobResponse)
def analyze_job(request: AnalyzeJobRequest, background_tasks: BackgroundTasks):
    run_id = request.run_id or str(uuid.uuid4())
    logger.info(f"POST /analyze-job run_id={run_id}")

    from backend.tools.jd_parser import parse_jd_rules
    from backend.agents.jd_reader_agent import _clean_skill_list, _clean_education_requirements, _clean_certifications

    # Always return fast using rule-based parser
    rule_data = parse_jd_rules(request.jd_text)
    rule_data["must_have_skills"] = _clean_skill_list(rule_data.get("must_have_skills", []))
    rule_data["preferred_skills"] = _clean_skill_list(rule_data.get("preferred_skills", []))
    rule_data["education_requirements"] = _clean_education_requirements(rule_data.get("education_requirements", []))
    rule_data["required_certifications"] = _clean_certifications(rule_data.get("required_certifications", []))
    job_profile = JobProfile(**rule_data)

    _jd_store[run_id] = request.jd_text
    storage.save_run(run_id, {
        "run_id": run_id,
        "raw_jd": request.jd_text,
        "job_profile": job_profile,
        "status": "jd_analyzed",
        "errors": [],
        "warnings": [],
    })

    # Enrich with LLM in background (updates storage when done)
    def _enrich_jd_with_llm():
        try:
            enriched = run_jd_reader_agent(request.jd_text)
            storage.update_run(run_id, {"job_profile": enriched})
            logger.info(f"LLM JD enrichment complete for run_id={run_id}")
        except Exception as e:
            logger.warning(f"LLM JD enrichment failed for run_id={run_id}: {e}")

    background_tasks.add_task(_enrich_jd_with_llm)

    return AnalyzeJobResponse(run_id=run_id, job_profile=job_profile)


@app.post("/upload-resumes", response_model=UploadResumesResponse)
async def upload_resumes(run_id: str, files: list[UploadFile] = File(...)):
    logger.info(f"POST /upload-resumes run_id={run_id} files={len(files)}")

    run_dir = Path(settings.upload_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    failed_files: list[str] = []

    for file in files:
        if not file.filename:
            failed_files.append("unnamed_file")
            continue

        suffix = Path(file.filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            failed_files.append(f"{file.filename} (unsupported format)")
            continue

        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            failed_files.append(f"{file.filename} (exceeds {settings.max_file_size_mb}MB limit)")
            continue

        dest = run_dir / file.filename
        dest.write_bytes(content)
        saved_paths.append(str(dest))
        logger.info(f"Saved: {dest}")

    _resume_store[run_id] = saved_paths

    existing = storage.get_run(run_id)
    if existing:
        storage.update_run(run_id, {"raw_resume_paths": saved_paths})
    else:
        storage.save_run(run_id, {
            "run_id": run_id,
            "raw_jd": "",
            "raw_resume_paths": saved_paths,
            "status": "resumes_uploaded",
            "errors": [],
            "warnings": [],
        })

    return UploadResumesResponse(
        run_id=run_id,
        uploaded_count=len(saved_paths),
        failed_files=failed_files,
        message=f"Uploaded {len(saved_paths)} resumes successfully",
    )


def _run_pipeline_task(run_id: str, jd_text: str, resume_paths: list[str]):
    try:
        storage.update_run(run_id, {"status": "processing"})
        final_state = run_pipeline(jd_text, resume_paths, run_id)
        ranked = final_state.get("ranked_candidates", [])
        job_profile = final_state.get("job_profile")
        export_to_csv(run_id, ranked)
        export_to_json(run_id, ranked, job_profile)
        export_shortlist_report(run_id, ranked, job_profile)
        storage.update_run(run_id, {
            "ranked_candidates": ranked,
            "job_profile": job_profile,
            "status": final_state.get("status", "completed"),
            "errors": final_state.get("errors", []),
            "warnings": final_state.get("warnings", []),
        })
    except Exception as e:
        logger.error(f"Background pipeline failed: {e}")
        storage.update_run(run_id, {"status": "failed", "errors": [str(e)]})


@app.post("/rank", response_model=RankResponse)
def rank_candidates(request: RankRequest, background_tasks: BackgroundTasks):
    run_id = request.run_id
    logger.info(f"POST /rank run_id={run_id}")

    run_state = storage.get_run(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found. Call /analyze-job first.")

    jd_text = _jd_store.get(run_id) or run_state.get("raw_jd", "")
    resume_paths = _resume_store.get(run_id) or run_state.get("raw_resume_paths", [])

    if not jd_text:
        raise HTTPException(status_code=400, detail="No job description found for this run.")
    if not resume_paths:
        raise HTTPException(status_code=400, detail="No resumes uploaded for this run.")

    background_tasks.add_task(_run_pipeline_task, run_id, jd_text, resume_paths)

    return RankResponse(
        run_id=run_id,
        total_candidates=len(resume_paths),
        shortlisted=0,
        on_hold=0,
        rejected=0,
        message="Ranking started. Poll /status/{run_id} for progress, then GET /results/{run_id} when completed.",
    )


@app.get("/status/{run_id}")
def get_status(run_id: str):
    state = storage.get_run(run_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    ranked = state.get("ranked_candidates", [])
    return {
        "run_id": run_id,
        "status": state.get("status", "unknown"),
        "total_candidates": len(ranked),
        "shortlisted": sum(1 for c in ranked if c.reasoning and c.reasoning.recommendation.value == "shortlist"),
        "on_hold": sum(1 for c in ranked if c.reasoning and c.reasoning.recommendation.value == "hold"),
        "rejected": sum(1 for c in ranked if c.reasoning and c.reasoning.recommendation.value == "reject"),
        "errors": state.get("errors", []),
    }


@app.get("/results/{run_id}", response_model=ResultsResponse)
def get_results(run_id: str):
    logger.info(f"GET /results/{run_id}")
    state = storage.get_run(run_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return ResultsResponse(
        run_id=run_id,
        job_profile=state.get("job_profile"),
        ranked_candidates=state.get("ranked_candidates", []),
        total=len(state.get("ranked_candidates", [])),
        errors=state.get("errors", []),
        warnings=state.get("warnings", []),
        status=state.get("status", "unknown"),
    )


@app.get("/download/{run_id}")
def download_results(run_id: str, format: str = "csv"):
    logger.info(f"GET /download/{run_id} format={format}")

    state = storage.get_run(run_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    ranked = state.get("ranked_candidates", [])
    if not ranked:
        raise HTTPException(status_code=404, detail="No ranked results available yet")

    job_profile = state.get("job_profile")

    if format == "csv":
        file_path = export_to_csv(run_id, ranked)
        media_type = "text/csv"
        filename = f"{run_id}_results.csv"
    elif format == "json":
        file_path = export_to_json(run_id, ranked, job_profile)
        media_type = "application/json"
        filename = f"{run_id}_results.json"
    elif format == "report":
        file_path = export_shortlist_report(run_id, ranked, job_profile)
        media_type = "text/plain"
        filename = f"{run_id}_shortlist_report.txt"
    else:
        raise HTTPException(status_code=400, detail="format must be csv, json, or report")

    if not Path(file_path).exists():
        raise HTTPException(status_code=500, detail="Export file not found")

    return FileResponse(path=file_path, media_type=media_type, filename=filename)
