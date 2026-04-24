import { useState, useCallback } from "react";
import { analyzeJob, uploadResumes, rankCandidates, getStatus, getResults } from "../services/api.js";

const STEPS = ["idle", "analyzing_jd", "uploading_resumes", "ranking", "completed", "error"];

export function usePipeline() {
  const [step, setStep] = useState("idle");
  const [runId, setRunId] = useState(null);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState({ message: "", percent: 0 });

  const reset = useCallback(() => {
    setStep("idle");
    setRunId(null);
    setResults(null);
    setError(null);
    setProgress({ message: "", percent: 0 });
  }, []);

  const run = useCallback(async (jdText, files) => {
    setError(null);
    setResults(null);

    try {
      setStep("analyzing_jd");
      setProgress({ message: "Analyzing job description...", percent: 15 });
      const jdResult = await analyzeJob(jdText);
      const currentRunId = jdResult.run_id;
      setRunId(currentRunId);

      setStep("uploading_resumes");
      setProgress({ message: `Uploading ${files.length} resume(s)...`, percent: 35 });
      await uploadResumes(currentRunId, files);

      setStep("ranking");
      setProgress({ message: "AI is ranking candidates...", percent: 60 });
      await rankCandidates(currentRunId);

      // Poll until pipeline completes
      const PENDING_STATUSES = ["processing", "started", "jd_parsed", "resumes_parsed", "ranked"];
      let status = "processing";
      let attempts = 0;
      while (PENDING_STATUSES.includes(status)) {
        await new Promise((r) => setTimeout(r, 3000));
        const s = await getStatus(currentRunId);
        status = s.status;
        attempts++;
        const pct = Math.min(60 + attempts * 4, 92);
        setProgress({ message: `Ranking in progress... (${status})`, percent: pct });
        if (attempts > 100) throw new Error("Ranking timed out after 5 minutes");
      }

      if (status === "failed") throw new Error("Ranking pipeline failed on server");

      setProgress({ message: "Fetching results...", percent: 95 });
      const finalResults = await getResults(currentRunId);
      setResults(finalResults);

      setStep("completed");
      setProgress({ message: "Ranking complete!", percent: 100 });
    } catch (err) {
      setError(err.message);
      setStep("error");
      setProgress({ message: "Pipeline failed", percent: 0 });
    }
  }, []);

  return { step, runId, results, error, progress, run, reset };
}
