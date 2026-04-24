import json
from pathlib import Path
from typing import Optional
from backend.core.state import PipelineState
from backend.core.logging import get_logger
from backend.core.config import settings

logger = get_logger(__name__)


class PydanticJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Pydantic v2
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        # Pydantic v1 fallback
        if hasattr(obj, "dict"):
            return obj.dict()
        # Enums (e.g., RoleType, Recommendation, ParseStatus)
        if hasattr(obj, "value"):
            return obj.value
        return super().default(obj)


class StorageService:
    def __init__(self):
        self._runs: dict[str, PipelineState] = {}
        self._persist_path = Path(settings.upload_dir) / "runs_state.json"
        self._load()

    def _reconstruct_state(self, data: dict) -> PipelineState:
        from backend.schemas.job import JobProfile
        from backend.schemas.candidate import CandidateProfile
        from backend.schemas.scoring import ScoredCandidate

        state = dict(data)

        if state.get("job_profile") and isinstance(state["job_profile"], dict):
            state["job_profile"] = JobProfile(**state["job_profile"])

        if state.get("candidate_profiles"):
            state["candidate_profiles"] = [
                CandidateProfile(**p) if isinstance(p, dict) else p
                for p in state["candidate_profiles"]
            ]

        if state.get("scored_candidates"):
            state["scored_candidates"] = [
                ScoredCandidate(**c) if isinstance(c, dict) else c
                for c in state["scored_candidates"]
            ]

        if state.get("ranked_candidates"):
            state["ranked_candidates"] = [
                ScoredCandidate(**c) if isinstance(c, dict) else c
                for c in state["ranked_candidates"]
            ]

        return state

    def _load(self) -> None:
        if self._persist_path.exists():
            try:
                with open(self._persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._runs = {
                    run_id: self._reconstruct_state(state)
                    for run_id, state in data.items()
                }
                logger.info(f"Loaded {len(self._runs)} runs from {self._persist_path}")
            except Exception as e:
                logger.warning(f"Failed to load runs state: {e}")
                self._runs = {}

    def _save(self) -> None:
        try:
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(self._runs, f, cls=PydanticJSONEncoder, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist runs state: {e}")

    def save_run(self, run_id: str, state: PipelineState) -> None:
        self._runs[run_id] = state
        self._save()
        logger.info(f"Saved run {run_id} with status={state.get('status', 'unknown')}")

    def get_run(self, run_id: str) -> Optional[PipelineState]:
        return self._runs.get(run_id)

    def update_run(self, run_id: str, updates: dict) -> None:
        if run_id in self._runs:
            self._runs[run_id].update(updates)
            self._save()
            logger.debug(f"Updated run {run_id}")
        else:
            logger.warning(f"Tried to update non-existent run {run_id}")

    def delete_run(self, run_id: str) -> None:
        if run_id in self._runs:
            del self._runs[run_id]
            self._save()
            logger.info(f"Deleted run {run_id}")

    def list_runs(self) -> list[str]:
        return list(self._runs.keys())


storage = StorageService()

