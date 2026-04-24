import React from "react";

export default function ScoreBadge({ score, size = "md" }) {
  const getColor = (s) => {
    if (s >= 70) return "bg-green-100 text-green-800 border-green-200";
    if (s >= 50) return "bg-yellow-100 text-yellow-800 border-yellow-200";
    return "bg-red-100 text-red-800 border-red-200";
  };

  const sizeClass = size === "lg" ? "text-2xl font-bold px-4 py-2" : "text-sm font-semibold px-2.5 py-1";

  return (
    <span className={`inline-flex items-center rounded-full border ${getColor(score)} ${sizeClass}`}>
      {score?.toFixed(1)}
    </span>
  );
}
