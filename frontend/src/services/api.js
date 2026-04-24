import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 60000,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      "An unexpected error occurred";
    return Promise.reject(new Error(message));
  }
);

export const analyzeJob = (jdText, runId = null) =>
  api.post("/analyze-job", { jd_text: jdText, run_id: runId }, { timeout: 120000 }).then((r) => r.data);

export const uploadResumes = (runId, files) => {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  return api.post(`/upload-resumes?run_id=${runId}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data);
};

export const rankCandidates = (runId) =>
  api.post("/rank", { run_id: runId }, { timeout: 10000 }).then((r) => r.data);

export const getStatus = (runId) =>
  api.get(`/status/${runId}`).then((r) => r.data);

export const getResults = (runId) =>
  api.get(`/results/${runId}`).then((r) => r.data);

export const getHealth = () =>
  api.get("/health").then((r) => r.data);

export const getDownloadUrl = (runId, format = "csv") =>
  `/api/download/${runId}?format=${format}`;
