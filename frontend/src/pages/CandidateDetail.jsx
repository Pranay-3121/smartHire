import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getResults } from "../services/api.js";
import ScoreBadge from "../components/ScoreBadge.jsx";
import RecommendationBadge from "../components/RecommendationBadge.jsx";
import ScoreBar from "../components/ScoreBar.jsx";

function Section({ title, children }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h3 className="text-base font-semibold text-gray-800 mb-4">{title}</h3>
      {children}
    </div>
  );
}

function TagList({ items, color = "gray" }) {
  const colors = {
    gray: "bg-gray-100 text-gray-700",
    green: "bg-green-100 text-green-700",
    red: "bg-red-100 text-red-700",
    yellow: "bg-yellow-100 text-yellow-700",
    blue: "bg-blue-100 text-blue-700",
  };
  return (
    <div className="flex flex-wrap gap-1.5">
      {items?.map((item, i) => (
        <span key={i} className={`text-xs px-2.5 py-1 rounded-full font-medium ${colors[color]}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

export default function CandidateDetail() {
  const { runId, candidateId } = useParams();
  const navigate = useNavigate();
  const [scored, setScored] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getResults(runId)
      .then((data) => {
        const found = data.ranked_candidates?.find(
          (sc) => sc.candidate.candidate_id === candidateId
        );
        if (!found) setError("Candidate not found in this run.");
        else setScored(found);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [runId, candidateId]);

  if (loading) return <div className="text-center py-20 text-gray-400">Loading candidate data...</div>;
  if (error) return <div className="text-center py-20 text-red-500">{error}</div>;
  if (!scored) return null;

  const { candidate: c, score_breakdown: sb, reasoning: r, rank } = scored;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button onClick={() => navigate(-1)} className="text-sm text-blue-600 hover:text-blue-800 font-medium">
        ← Back to Results
      </button>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-blue-600">#{rank}</span>
              <h1 className="text-2xl font-bold text-gray-900">{c.name || "Unknown Candidate"}</h1>
            </div>
            <div className="mt-2 flex flex-wrap gap-3 text-sm text-gray-500">
              {c.email && <span>✉ {c.email}</span>}
              {c.phone && <span>📞 {c.phone}</span>}
              {c.location && <span>📍 {c.location}</span>}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <ScoreBadge score={sb?.total_score} size="lg" />
            {r && <RecommendationBadge recommendation={r.recommendation} />}
          </div>
        </div>
        {c.summary && <p className="mt-4 text-sm text-gray-600">{c.summary}</p>}
        {r?.summary && <p className="mt-3 text-sm text-gray-700 bg-blue-50 p-3 rounded-lg">{r.summary}</p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Score Breakdown */}
        <Section title="📊 Score Breakdown">
          <ScoreBar breakdown={sb} />
          <div className="mt-3 pt-3 border-t flex justify-between text-sm font-semibold">
            <span>Total Score</span>
            <span className="text-blue-700">{sb?.total_score?.toFixed(1)} / 100</span>
          </div>
        </Section>

        {/* Reasoning */}
        {r && (
          <Section title="🧠 AI Reasoning">
            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Strengths</p>
                <ul className="space-y-1">
                  {r.strengths?.map((s, i) => (
                    <li key={i} className="text-sm text-green-700 flex gap-2">
                      <span>✓</span><span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Gaps</p>
                <ul className="space-y-1">
                  {r.gaps?.map((g, i) => (
                    <li key={i} className="text-sm text-red-600 flex gap-2">
                      <span>✗</span><span>{g}</span>
                    </li>
                  ))}
                </ul>
              </div>
              {r.risks?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Risks</p>
                  <ul className="space-y-1">
                    {r.risks?.map((risk, i) => (
                      <li key={i} className="text-sm text-amber-600 flex gap-2">
                        <span>⚠</span><span>{risk}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="pt-2 border-t text-sm text-gray-500">
                Confidence: <strong>{(r.confidence_level * 100)?.toFixed(0)}%</strong>
              </div>
            </div>
          </Section>
        )}
      </div>

      {/* Skills */}
      <Section title="🛠 Skills">
        <TagList items={c.skills} color="blue" />
      </Section>

      {/* Work Experience */}
      {c.work_experience?.length > 0 && (
        <Section title="💼 Work Experience">
          <div className="space-y-4">
            {c.work_experience.map((w, i) => (
              <div key={i} className="border-l-2 border-blue-200 pl-4">
                <p className="font-semibold text-gray-800">{w.title}</p>
                <p className="text-sm text-gray-600">{w.company}</p>
                <p className="text-xs text-gray-400">
                  {w.start_date} — {w.end_date || "Present"}
                  {w.duration_months ? ` (${w.duration_months} months)` : ""}
                </p>
                {w.description && <p className="text-sm text-gray-600 mt-1">{w.description}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Education */}
      {c.education?.length > 0 && (
        <Section title="🎓 Education">
          <div className="space-y-3">
            {c.education.map((e, i) => (
              <div key={i}>
                <p className="font-semibold text-gray-800">{e.degree}</p>
                <p className="text-sm text-gray-600">{e.institution}</p>
                {e.graduation_year && <p className="text-xs text-gray-400">{e.graduation_year}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Projects */}
      {c.projects?.length > 0 && (
        <Section title="🚀 Projects">
          <div className="space-y-4">
            {c.projects.map((p, i) => (
              <div key={i}>
                <p className="font-semibold text-gray-800">{p.name}</p>
                <p className="text-sm text-gray-600">{p.description}</p>
                {p.technologies?.length > 0 && (
                  <div className="mt-1">
                    <TagList items={p.technologies} color="gray" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Certifications */}
      {c.certifications?.length > 0 && (
        <Section title="🏆 Certifications">
          <TagList items={c.certifications} color="green" />
        </Section>
      )}

      {/* Warning Flags */}
      {c.warning_flags?.length > 0 && (
        <Section title="⚠ Warning Flags">
          <TagList items={c.warning_flags} color="yellow" />
        </Section>
      )}
    </div>
  );
}
