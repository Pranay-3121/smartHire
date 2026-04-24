import React from "react";

function DimensionBar({ label, rawScore, weightedScore, weight }) {
  const pct = Math.min(rawScore, 100);
  const barColor = pct >= 70 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span className="font-medium">{label}</span>
        <span>{rawScore?.toFixed(1)} / 100 <span className="text-gray-400">(weight {weight}%)</span></span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div className={`${barColor} h-2 rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function ScoreBar({ breakdown }) {
  if (!breakdown) return null;

  const dimensions = [
    { label: "Role Experience", key: "role_experience" },
    { label: "Relevant Projects", key: "relevant_projects" },
    { label: "Certifications", key: "certifications" },
    { label: "Education", key: "education" },
    { label: "Soft Signals", key: "soft_signals" },
  ];

  return (
    <div className="space-y-3">
      {dimensions.map(({ label, key }) => {
        const dim = breakdown[key];
        if (!dim) return null;
        return (
          <DimensionBar
            key={key}
            label={label}
            rawScore={dim.raw_score}
            weightedScore={dim.weighted_score}
            weight={dim.weight}
          />
        );
      })}
      {breakdown.penalty_deductions > 0 && (
        <p className="text-xs text-red-600 font-medium">
          ⚠ Penalty deductions: -{breakdown.penalty_deductions?.toFixed(1)} pts
        </p>
      )}
      <div className="flex justify-between text-xs text-gray-500 pt-1 border-t">
        <span>Semantic similarity</span>
        <span>{(breakdown.semantic_similarity * 100)?.toFixed(1)}%</span>
      </div>
    </div>
  );
}
