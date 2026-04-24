import React, { useState, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import CandidateCard from "../components/CandidateCard.jsx";
import { getDownloadUrl } from "../services/api.js";

const FILTER_OPTIONS = ["all", "shortlist", "hold", "reject"];

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  const { runId, results } = location.state || {};

  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sortBy, setSortBy] = useState("rank");

  if (!results || !runId) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500 text-lg">No results to display.</p>
        <button
          onClick={() => navigate("/")}
          className="mt-4 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
        >
          Go to Dashboard
        </button>
      </div>
    );
  }

  const candidates = results.ranked_candidates || [];
  const job = results.job_profile;

  const filtered = useMemo(() => {
    let list = [...candidates];

    if (filter !== "all") {
      list = list.filter((sc) => sc.reasoning?.recommendation === filter);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((sc) =>
        sc.candidate.name?.toLowerCase().includes(q) ||
        sc.candidate.email?.toLowerCase().includes(q) ||
        sc.candidate.skills?.some((s) => s.toLowerCase().includes(q))
      );
    }

    if (sortBy === "rank") list.sort((a, b) => (a.rank || 0) - (b.rank || 0));
    else if (sortBy === "score") list.sort((a, b) => b.score_breakdown.total_score - a.score_breakdown.total_score);
    else if (sortBy === "experience") list.sort((a, b) => b.candidate.total_experience_years - a.candidate.total_experience_years);

    return list;
  }, [candidates, filter, search, sortBy]);

  const stats = useMemo(() => ({
    total: candidates.length,
    shortlisted: candidates.filter((c) => c.reasoning?.recommendation === "shortlist").length,
    hold: candidates.filter((c) => c.reasoning?.recommendation === "hold").length,
    rejected: candidates.filter((c) => c.reasoning?.recommendation === "reject").length,
  }), [candidates]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ranking Results</h1>
          {job && (
            <p className="text-gray-500 mt-1">
              {job.role_title} · {job.role_type} · Min {job.min_experience_years}y exp
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <a href={getDownloadUrl(runId, "csv")} download className="text-sm bg-white border border-gray-300 text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors">
            ⬇ CSV
          </a>
          <a href={getDownloadUrl(runId, "json")} download className="text-sm bg-white border border-gray-300 text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors">
            ⬇ JSON
          </a>
          <a href={getDownloadUrl(runId, "report")} download className="text-sm bg-blue-600 text-white px-3 py-2 rounded-lg hover:bg-blue-700 transition-colors">
            ⬇ Report
          </a>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total", value: stats.total, color: "text-gray-900" },
          { label: "Shortlisted", value: stats.shortlisted, color: "text-green-700" },
          { label: "On Hold", value: stats.hold, color: "text-yellow-700" },
          { label: "Rejected", value: stats.rejected, color: "text-red-700" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-4 text-center shadow-sm">
            <p className={`text-3xl font-bold ${color}`}>{value}</p>
            <p className="text-sm text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Search by name, email, or skill..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-48 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex gap-1">
          {FILTER_OPTIONS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                filter === f ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="rank">Sort: Rank</option>
          <option value="score">Sort: Score</option>
          <option value="experience">Sort: Experience</option>
        </select>
      </div>

      {/* Errors/Warnings */}
      {results.errors?.length > 0 && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <strong>Errors:</strong> {results.errors.join(", ")}
        </div>
      )}

      {/* Candidate List */}
      <div className="space-y-4">
        {filtered.length === 0 ? (
          <div className="text-center py-12 text-gray-400">No candidates match your filters.</div>
        ) : (
          filtered.map((sc) => (
            <CandidateCard key={sc.candidate.candidate_id} scored={sc} runId={runId} />
          ))
        )}
      </div>
    </div>
  );
}
