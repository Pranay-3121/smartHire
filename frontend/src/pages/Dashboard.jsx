import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePipeline } from "../hooks/usePipeline.js";
import FileDropzone from "../components/FileDropzone.jsx";
import ProgressBar from "../components/ProgressBar.jsx";

const STEP_LABELS = {
  idle: null,
  analyzing_jd: "Analyzing Job Description",
  uploading_resumes: "Uploading Resumes",
  ranking: "AI Ranking in Progress",
  completed: "Completed",
  error: "Error",
};

export default function Dashboard() {
  const [jdText, setJdText] = useState("");
  const [resumeFiles, setResumeFiles] = useState([]);
  const { step, runId, results, error, progress, run, reset } = usePipeline();
  const navigate = useNavigate();

  const isRunning = ["analyzing_jd", "uploading_resumes", "ranking"].includes(step);
  const canRun = jdText.trim().length >= 50 && resumeFiles.length > 0 && !isRunning;

  const handleRun = async () => {
    await run(jdText, resumeFiles);
  };

  const handleViewResults = () => {
    navigate("/results", { state: { runId, results } });
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">AI Resume Ranker</h1>
        <p className="text-gray-500 mt-1">Upload a job description and resumes to get AI-powered candidate rankings.</p>
      </div>

      {/* Step 1: Job Description */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-blue-600 text-white text-sm flex items-center justify-center font-bold">1</span>
          Job Description
        </h2>
        <textarea
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          placeholder="Paste the full job description here (minimum 50 characters)..."
          rows={10}
          disabled={isRunning}
          className="w-full border border-gray-300 rounded-lg p-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y disabled:bg-gray-50 disabled:cursor-not-allowed"
        />
        <p className="text-xs text-gray-400 mt-1">{jdText.length} characters</p>
      </div>

      {/* Step 2: Upload Resumes */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-blue-600 text-white text-sm flex items-center justify-center font-bold">2</span>
          Upload Resumes
        </h2>
        <FileDropzone
          files={resumeFiles}
          onChange={setResumeFiles}
          accept=".pdf,.docx,.txt"
          multiple
          label="Upload PDF, DOCX, or TXT resumes"
        />
        {resumeFiles.length > 0 && (
          <p className="text-sm text-gray-500 mt-2">{resumeFiles.length} file(s) selected</p>
        )}
      </div>

      {/* Step 3: Run */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-blue-600 text-white text-sm flex items-center justify-center font-bold">3</span>
          Run AI Ranking
        </h2>

        {isRunning && (
          <div className="mb-4">
            <ProgressBar percent={progress.percent} message={progress.message} />
          </div>
        )}

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            <strong>Error:</strong> {error}
          </div>
        )}

        {step === "completed" && results && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
            ✅ Ranking complete! {results.total} candidates ranked.
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleRun}
            disabled={!canRun}
            className="flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isRunning ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                {STEP_LABELS[step]}...
              </span>
            ) : "🚀 Run AI Ranking"}
          </button>

          {step === "completed" && (
            <button
              onClick={handleViewResults}
              className="bg-green-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-green-700 transition-colors"
            >
              View Results →
            </button>
          )}

          {(step === "completed" || step === "error") && (
            <button
              onClick={reset}
              className="bg-gray-100 text-gray-700 py-3 px-4 rounded-lg font-medium hover:bg-gray-200 transition-colors"
            >
              Reset
            </button>
          )}
        </div>

        {!canRun && !isRunning && (
          <p className="text-xs text-gray-400 mt-2">
            {jdText.trim().length < 50 ? "• Add a job description (min 50 chars)" : ""}
            {resumeFiles.length === 0 ? " • Upload at least one resume" : ""}
          </p>
        )}
      </div>
    </div>
  );
}
