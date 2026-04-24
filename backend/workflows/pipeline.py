import uuid
from langgraph.graph import StateGraph, END
from backend.core.state import PipelineState
from backend.agents.jd_reader_agent import run_jd_reader_agent
from backend.agents.resume_parser_agent import run_resume_parser_agent
from backend.agents.ranking_agent import run_ranking_agent
from backend.agents.reasoning_agent import run_reasoning_agent
from backend.services.storage import storage
from backend.core.logging import get_logger

logger = get_logger(__name__)


def node_read_jd(state: PipelineState) -> PipelineState:
    logger.info(f"[Pipeline] Node: read_jd | run_id={state['run_id']}")
    try:
        job_profile = run_jd_reader_agent(state["raw_jd"])
        logger.info(
            f"[Pipeline:jd_parsed] run_id={state['run_id']} "
            f"role='{job_profile.role_title}' type={job_profile.role_type} "
            f"must_have={len(job_profile.must_have_skills)} preferred={len(job_profile.preferred_skills)} "
            f"min_exp={job_profile.min_experience_years}"
        )
        return {**state, "job_profile": job_profile, "status": "jd_parsed"}
    except Exception as e:
        logger.error(f"JD parsing failed: {e}")
        errors = state.get("errors", []) + [f"JD parsing error: {str(e)}"]
        return {**state, "errors": errors, "status": "failed"}


def node_parse_resumes(state: PipelineState) -> PipelineState:
    logger.info(f"[Pipeline] Node: parse_resumes | run_id={state['run_id']}")
    try:
        profiles = run_resume_parser_agent(state.get("raw_resume_paths", []))
        warnings = state.get("warnings", [])
        for p in profiles:
            warnings.extend(p.warning_flags)
        logger.info(
            f"[Pipeline:resumes_parsed] run_id={state['run_id']} "
            f"profiles={len(profiles)} "
            f"valid={sum(1 for p in profiles if p.parse_status != 'failed')} "
            f"failed={sum(1 for p in profiles if p.parse_status == 'failed')}"
        )
        return {**state, "candidate_profiles": profiles, "warnings": warnings, "status": "resumes_parsed"}
    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        errors = state.get("errors", []) + [f"Resume parsing error: {str(e)}"]
        return {**state, "errors": errors, "status": "failed"}


def node_rank_candidates(state: PipelineState) -> PipelineState:
    logger.info(f"[Pipeline] Node: rank_candidates | run_id={state['run_id']}")
    try:
        scored = run_ranking_agent(
            state.get("candidate_profiles", []),
            state["job_profile"],
            state["run_id"],
        )
        logger.info(
            f"[Pipeline:ranked] run_id={state['run_id']} "
            f"scored={len(scored)} "
        )
        return {**state, "scored_candidates": scored, "status": "ranked"}
    except Exception as e:
        logger.error(f"Ranking failed: {e}")
        errors = state.get("errors", []) + [f"Ranking error: {str(e)}"]
        return {**state, "errors": errors, "status": "failed"}


def node_generate_reasoning(state: PipelineState) -> PipelineState:
    logger.info(f"[Pipeline] Node: generate_reasoning | run_id={state['run_id']}")
    try:
        ranked = run_reasoning_agent(
            state.get("scored_candidates", []),
            state["job_profile"],
        )
        # Count recommendations
        shortlist = sum(1 for c in ranked if c.reasoning and c.reasoning.recommendation.value == "shortlist")
        hold = sum(1 for c in ranked if c.reasoning and c.reasoning.recommendation.value == "hold")
        reject = sum(1 for c in ranked if c.reasoning and c.reasoning.recommendation.value == "reject")
        logger.info(
            f"[Pipeline:completed] run_id={state['run_id']} "
            f"shortlist={shortlist} hold={hold} reject={reject}"
        )
        return {**state, "ranked_candidates": ranked, "status": "completed"}
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
        errors = state.get("errors", []) + [f"Reasoning error: {str(e)}"]
        ranked = state.get("scored_candidates", [])
        return {**state, "ranked_candidates": ranked, "errors": errors, "status": "completed_with_errors"}


def _should_continue(state: PipelineState) -> str:
    if state.get("status") == "failed":
        return END
    return "continue"


def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("read_jd", node_read_jd)
    graph.add_node("parse_resumes", node_parse_resumes)
    graph.add_node("rank_candidates", node_rank_candidates)
    graph.add_node("generate_reasoning", node_generate_reasoning)

    graph.set_entry_point("read_jd")

    graph.add_conditional_edges("read_jd", _should_continue, {"continue": "parse_resumes", END: END})
    graph.add_conditional_edges("parse_resumes", _should_continue, {"continue": "rank_candidates", END: END})
    graph.add_conditional_edges("rank_candidates", _should_continue, {"continue": "generate_reasoning", END: END})
    graph.add_edge("generate_reasoning", END)

    return graph.compile()


def run_pipeline(jd_text: str, resume_paths: list[str], run_id: str | None = None) -> PipelineState:
    run_id = run_id or str(uuid.uuid4())
    logger.info(f"Starting pipeline run_id={run_id} with {len(resume_paths)} resumes")

    initial_state: PipelineState = {
        "run_id": run_id,
        "raw_jd": jd_text,
        "raw_resume_paths": resume_paths,
        "candidate_profiles": [],
        "scored_candidates": [],
        "ranked_candidates": [],
        "errors": [],
        "warnings": [],
        "status": "started",
    }

    storage.save_run(run_id, initial_state)

    pipeline = build_pipeline()
    final_state = pipeline.invoke(initial_state)

    storage.save_run(run_id, final_state)
    logger.info(f"Pipeline completed run_id={run_id} status={final_state.get('status')}")
    return final_state
