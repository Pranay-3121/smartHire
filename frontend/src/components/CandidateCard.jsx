import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import ScoreBadge from "./ScoreBadge.jsx";
import RecommendationBadge from "./RecommendationBadge.jsx";
import ScoreBar from "./ScoreBar.jsx";

export default function CandidateCard({ scored, runId }) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();
  const { candidate, score_breakdown, reasoning, rank } = scored;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-sm">
              #{rank}
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-gray-900 truncate">
                {candidate.name || "Unknown Candidate"}
              </h3>
              <p className="text-sm text-gray-500 truncate">{candidate.email || "No email"}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <ScoreBadge score={score_breakdown?.total_score} />
            {reasoning && <RecommendationBadge recommendation={reasoning.recommendation} />}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {candidate.skills?.slice(0, 8).map((skill) => (
            <span key={skill} className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full">
              {skill}
            </span>
          ))}
          {candidate.skills?.length > 8 && (
            <span className="text-xs text-gray-400">+{candidate.skills.length - 8} more</span>
          )}
        </div>

        <div className="mt-3 flex items-center gap-4 text-sm text-gray-500">
          <span>📅 {candidate.total_experience_years}y exp</span>
          {candidate.certifications?.length > 0 && (
            <span>🏆 {candidate.certifications.length} cert(s)</span>
          )}
          {candidate.warning_flags?.length > 0 && (
            <span className="text-amber-600">⚠ {candidate.warning_flags.length} flag(s)</span>
          )}
        </div>

        {reasoning?.summary && (
          <p className="mt-3 text-sm text-gray-600 line-clamp-2">{reasoning.summary}</p>
        )}

        <div className="mt-4 flex items-center gap-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            {expanded ? "Hide breakdown ▲" : "Show breakdown ▼"}
          </button>
          <button
            onClick={() => navigate(`/candidate/${runId}/${candidate.candidate_id}`)}
            className="ml-auto text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 transition-colors"
          >
            View Details →
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-100 p-5 bg-gray-50 rounded-b-xl">
          <ScoreBar breakdown={score_breakdown} />
        </div>
      )}
    </div>
  );
}
