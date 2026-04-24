import React from "react";

const CONFIG = {
  shortlist: { label: "Shortlist", className: "bg-green-100 text-green-800 border-green-200" },
  hold: { label: "Hold", className: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  reject: { label: "Reject", className: "bg-red-100 text-red-800 border-red-200" },
};

export default function RecommendationBadge({ recommendation }) {
  const config = CONFIG[recommendation] || CONFIG.hold;
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${config.className}`}>
      {config.label}
    </span>
  );
}
