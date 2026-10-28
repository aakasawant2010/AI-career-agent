import {
  AlertCircle,
  ArrowUpRight,
  BrainCircuit,
  BriefcaseBusiness,
  CheckCircle2,
  ChevronRight,
  Clock3,
  MapPin,
  Search,
  Sparkles,
  Target,
  X,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  applicationsApi,
  jobsApi,
  type Job,
  type JobMatch,
  type JobRecommendation,
} from "../api/services";

type JobWithMatch = Job & {
  match_score?: number;
  score?: number;
  recommendation?: string;
  matched_skills?: string[];
  missing_skills?: string[];
  risk?: string;
  risks?: string[];
};

function getScore(job: JobWithMatch) {
  return job.match_score ?? job.score ?? 0;
}

function getRecommendationClass(recommendation?: string) {
  const value = recommendation?.toLowerCase();

  if (
    value?.includes("strong") ||
    value?.includes("excellent")
  ) {
    return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  }

  if (
    value?.includes("good") ||
    value?.includes("match")
  ) {
    return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
  }

  if (
    value?.includes("weak") ||
    value?.includes("poor")
  ) {
    return "bg-rose-500/10 text-rose-400 border-rose-500/20";
  }

  return "bg-slate-800 text-slate-300 border-slate-700";
}

function ScoreRing({ score }: { score: number }) {
  const safeScore = Math.max(
    0,
    Math.min(100, Math.round(score))
  );

  const radius = 25;
  const circumference = 2 * Math.PI * radius;
  const offset =
    circumference -
    (safeScore / 100) * circumference;

  return (
    <div className="relative h-16 w-16 shrink-0">
      <svg
        className="h-16 w-16 -rotate-90"
        viewBox="0 0 64 64"
      >
        <circle
          cx="32"
          cy="32"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="5"
          className="text-slate-800"
        />

        <circle
          cx="32"
          cy="32"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="text-cyan-400"
        />
      </svg>

      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm font-bold">
          {safeScore}%
        </span>
      </div>
    </div>
  );
}

function JobModal({
  job,
  onClose,
  onMatch,
  onAnalyze,
  matching,
  analyzing,
  match,
  analysis,
}: {
  job: JobWithMatch;
  onClose: () => void;
  onMatch: () => void;
  onAnalyze: () => void;
  matching: boolean;
  analyzing: boolean;
  match?: JobMatch | null;
  analysis?: unknown;
}) {
  const score = match
    ? match.match_score ?? match.score ?? 0
    : getScore(job);

  const matchedSkills =
    match?.matched_skills ??
    job.matched_skills ??
    [];

  const missingSkills =
    match?.missing_skills ??
    job.missing_skills ??
    [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl">
        <div className="sticky top-0 z-10 flex items-start justify-between border-b border-slate-800 bg-slate-950/95 p-6 backdrop-blur">
          <div className="pr-6">
            <div className="flex items-center gap-2 text-sm text-cyan-400">
              <BriefcaseBusiness className="h-4 w-4" />
              {job.company}
            </div>

            <h2 className="mt-2 text-2xl font-bold">
              {job.title}
            </h2>

            <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-400">
              {job.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-4 w-4" />
                  {job.location}
                </span>
              )}

              {job.work_mode && (
                <span className="rounded-full bg-slate-800 px-3 py-1">
                  {job.work_mode}
                </span>
              )}

              {job.employment_type && (
                <span className="rounded-full bg-slate-800 px-3 py-1">
                  {job.employment_type}
                </span>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-8 p-6">
          <div className="grid gap-5 md:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-sm text-slate-400">
                Match Score
              </p>

              <div className="mt-4 flex items-center gap-4">
                <ScoreRing score={score} />

                <div>
                  <p className="font-semibold">
                    {score >= 80
                      ? "Strong match"
                      : score >= 60
                        ? "Good match"
                        : "Needs review"}
                  </p>

                  <p className="text-xs text-slate-500">
                    Based on your candidate profile
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-sm text-slate-400">
                Salary
              </p>

              <p className="mt-4 text-xl font-bold">
                {job.salary_text ??
                  (job.min_salary_lpa ||
                  job.max_salary_lpa
                    ? `${job.min_salary_lpa ?? ""} - ${job.max_salary_lpa ?? ""} LPA`
                    : "Not specified")}
              </p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-sm text-slate-400">
                Experience
              </p>

              <p className="mt-4 text-xl font-bold">
                {job.experience_min_years ||
                job.experience_max_years
                  ? `${job.experience_min_years ?? 0}-${job.experience_max_years ?? "∞"} years`
                  : "Not specified"}
              </p>
            </div>
          </div>

          {matchedSkills.length > 0 && (
            <section>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                <h3 className="font-semibold">
                  Matched Skills
                </h3>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {matchedSkills.map((skill) => (
                  <span
                    key={skill}
                    className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-sm text-emerald-300"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </section>
          )}

          {missingSkills.length > 0 && (
            <section>
              <div className="flex items-center gap-2">
                <XCircle className="h-5 w-5 text-amber-400" />
                <h3 className="font-semibold">
                  Missing Skills
                </h3>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {missingSkills.map((skill) => (
                  <span
                    key={skill}
                    className="rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1.5 text-sm text-amber-300"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </section>
          )}

          {job.description && (
            <section>
              <h3 className="font-semibold">
                Job Description
              </h3>

              <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-400">
                {job.description}
              </p>
            </section>
          )}

          {job.requirements && (
            <section>
              <h3 className="font-semibold">
                Requirements
              </h3>

              <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-400">
                {job.requirements}
              </p>
            </section>
          )}

          {analysis ? (
            <section>
              <div className="flex items-center gap-2">
                <BrainCircuit className="h-5 w-5 text-cyan-400" />

                <h3 className="font-semibold">
                  AI Analysis
                </h3>
              </div>

              <pre className="mt-4 max-h-96 overflow-auto rounded-xl border border-slate-800 bg-slate-950 p-4 text-xs leading-6 text-slate-300">
                {typeof analysis === "string"
                  ? analysis
                  : JSON.stringify(
                      analysis,
                      null,
                      2
                    )}
              </pre>
            </section>
          ) : null}

          <div className="flex flex-wrap gap-3 border-t border-slate-800 pt-6">
            <button
              onClick={onMatch}
              disabled={matching}
              className="flex items-center gap-2 rounded-lg bg-cyan-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Target className="h-4 w-4" />

              {matching
                ? "Matching..."
                : "Match Me"}
            </button>

            <button
              onClick={onAnalyze}
              disabled={analyzing}
              className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-5 py-2.5 text-sm font-semibold transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4 text-cyan-400" />

              {analyzing
                ? "Analyzing..."
                : "AI Analysis"}
            </button>

            {job.apply_url && (
              <a
                href={job.apply_url}
                target="_blank"
                rel="noreferrer"
                className="ml-auto flex items-center gap-2 rounded-lg border border-slate-700 px-5 py-2.5 text-sm font-semibold transition hover:bg-slate-800"
              >
                Open Application
                <ArrowUpRight className="h-4 w-4" />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Jobs() {
  const [jobs, setJobs] = useState<JobWithMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [workMode, setWorkMode] = useState("all");

  const [selectedJob, setSelectedJob] =
    useState<JobWithMatch | null>(null);

  const [match, setMatch] =
    useState<JobMatch | null>(null);

  const [analysis, setAnalysis] =
    useState<unknown | null>(null);

  const [matching, setMatching] =
    useState(false);

  const [analyzing, setAnalyzing] =
    useState(false);

  const [applyingJobId, setApplyingJobId] =
    useState<string | null>(null);

  const [applyMessage, setApplyMessage] =
    useState("");

  const loadJobs = async () => {
    try {
      setLoading(true);
      setError("");

      const [
        jobsResponse,
        recommendationsResponse,
      ] = await Promise.all([
        jobsApi.list(),
        jobsApi.recommendations().catch(() => []),
      ]);

      const recommendationMap =
        new Map<string, JobRecommendation>();

      recommendationsResponse.forEach((item) => {
        if (item.id) {
          recommendationMap.set(item.id, item);
        }
      });

      const merged = jobsResponse.map((job) => {
        const recommendation =
          recommendationMap.get(job.id);

        return {
          ...job,
          ...recommendation,
        };
      });

      setJobs(merged);

      const jobsWithMatches = await Promise.all(
        merged.map(async (job) => {
          try {
            const result =
              await jobsApi.match(job.id);

            return {
              ...job,
              match_score:
                result.match_score ??
                result.score ??
                0,
              score:
                result.score ??
                result.match_score ??
                0,
              recommendation:
                result.recommendation ??
                job.recommendation,
              matched_skills:
                result.matched_skills ??
                job.matched_skills,
              missing_skills:
                result.missing_skills ??
                job.missing_skills,
              risk: result.risk,
              risks: result.risks,
            };
          } catch {
            return job;
          }
        })
      );

      setJobs(jobsWithMatches);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ??
          "Unable to load jobs."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadJobs();
  }, []);

  const filteredJobs = useMemo(() => {
    const query =
      search.trim().toLowerCase();

    return jobs.filter((job) => {
      const searchable = [
        job.title,
        job.company,
        job.location,
        job.description,
        ...(job.skills ?? []),
        ...(job.technologies ?? []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesSearch =
        !query ||
        searchable.includes(query);

      const matchesWorkMode =
        workMode === "all" ||
        job.work_mode?.toLowerCase() ===
          workMode.toLowerCase();

      return (
        matchesSearch &&
        matchesWorkMode
      );
    });
  }, [jobs, search, workMode]);

  const workModes = useMemo(() => {
    const modes = new Set<string>();

    jobs.forEach((job) => {
      if (job.work_mode) {
        modes.add(job.work_mode);
      }
    });

    return Array.from(modes);
  }, [jobs]);

  const openJob = (job: JobWithMatch) => {
    setSelectedJob(job);
    setMatch(null);
    setAnalysis(null);
    setApplyMessage("");
  };

  const handleMatch = async () => {
    if (!selectedJob) return;

    try {
      setMatching(true);

      const result =
        await jobsApi.match(
          selectedJob.id
        );

      setMatch(result);

      const score =
        result.match_score ??
        result.score ??
        0;

      const updatedJob = {
        ...selectedJob,
        match_score: score,
        score,
        recommendation:
          result.recommendation,
        matched_skills:
          result.matched_skills,
        missing_skills:
          result.missing_skills,
        risk: result.risk,
        risks: result.risks,
      };

      setJobs((current) =>
        current.map((job) =>
          job.id === selectedJob.id
            ? updatedJob
            : job
        )
      );

      setSelectedJob(updatedJob);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ??
          "Unable to calculate match."
      );
    } finally {
      setMatching(false);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedJob) return;

    try {
      setAnalyzing(true);

      const result =
        await jobsApi.analyze(
          selectedJob.id
        );

      setAnalysis(result);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ??
          "Unable to analyze this job."
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const handleApply = async (
    job: JobWithMatch
  ) => {
    try {
      setApplyingJobId(job.id);
      setApplyMessage("");

      await applicationsApi.create({
        job_id: job.id,
        submission_mode:
          "MANUAL_SUBMISSION_REQUIRED",
      });

      setApplyMessage(
        `Application created for ${job.company}.`
      );
    } catch (err: any) {
      setApplyMessage(
        err?.response?.data?.detail ??
          "Unable to create application."
      );
    } finally {
      setApplyingJobId(null);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-cyan-400" />

              <h1 className="text-3xl font-bold">
                Job Discovery
              </h1>
            </div>

            <p className="mt-2 text-slate-400">
              Discover opportunities and let AI
              evaluate your fit.
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
            <p className="text-xs text-slate-500">
              Available Jobs
            </p>

            <p className="mt-1 text-xl font-bold">
              {jobs.length}
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-300">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />

          <div className="flex-1">
            {error}
          </div>

          <button
            onClick={() => setError("")}
            className="text-rose-300 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-500" />

            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search jobs, companies, skills..."
              className="w-full rounded-xl border border-slate-800 bg-slate-950 py-3 pl-12 pr-4 text-sm outline-none transition placeholder:text-slate-600 focus:border-cyan-500/50"
            />
          </div>

          <select
            value={workMode}
            onChange={(event) =>
              setWorkMode(event.target.value)
            }
            className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-300 outline-none focus:border-cyan-500/50"
          >
            <option value="all">
              All Work Modes
            </option>

            {workModes.map((mode) => (
              <option
                key={mode}
                value={mode}
              >
                {mode}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && (
        <div className="grid gap-5 xl:grid-cols-2">
          {Array.from({ length: 6 }).map(
            (_, index) => (
              <div
                key={index}
                className="animate-pulse rounded-2xl border border-slate-800 bg-slate-900 p-6"
              >
                <div className="h-5 w-2/3 rounded bg-slate-800" />
                <div className="mt-3 h-4 w-1/3 rounded bg-slate-800" />
                <div className="mt-6 h-16 rounded bg-slate-800" />
                <div className="mt-6 h-10 rounded bg-slate-800" />
              </div>
            )
          )}
        </div>
      )}

      {!loading &&
        filteredJobs.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/50 p-16 text-center">
            <BriefcaseBusiness className="mx-auto h-10 w-10 text-slate-600" />

            <h3 className="mt-4 text-lg font-semibold">
              No jobs found
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              Try changing your search or filters.
            </p>
          </div>
        )}

      {!loading &&
        filteredJobs.length > 0 && (
          <div className="grid gap-5 xl:grid-cols-2">
            {filteredJobs.map((job) => {
              const score =
                getScore(job);

              return (
                <div
                  key={job.id}
                  className="group rounded-2xl border border-slate-800 bg-slate-900 p-6 transition hover:-translate-y-0.5 hover:border-cyan-500/30 hover:bg-slate-900/90"
                >
                  <div className="flex gap-5">
                    <ScoreRing
                      score={score}
                    />

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-cyan-400">
                            {job.company}
                          </p>

                          <h2 className="mt-1 text-lg font-bold">
                            {job.title}
                          </h2>
                        </div>

                        {job.recommendation && (
                          <span
                            className={`rounded-full border px-2.5 py-1 text-xs font-medium ${getRecommendationClass(
                              job.recommendation
                            )}`}
                          >
                            {job.recommendation}
                          </span>
                        )}
                      </div>

                      <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                        {job.location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3.5 w-3.5" />
                            {job.location}
                          </span>
                        )}

                        {job.work_mode && (
                          <span className="flex items-center gap-1">
                            <BriefcaseBusiness className="h-3.5 w-3.5" />
                            {job.work_mode}
                          </span>
                        )}

                        {job.notice_period_days && (
                          <span className="flex items-center gap-1">
                            <Clock3 className="h-3.5 w-3.5" />
                            {job.notice_period_days}d notice
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {(job.skills?.length ?? 0) > 0 && (
                    <div className="mt-6 flex flex-wrap gap-2">
                      {job.skills
                        ?.slice(0, 6)
                        .map((skill) => (
                          <span
                            key={skill}
                            className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-300"
                          >
                            {skill}
                          </span>
                        ))}

                      {(job.skills?.length ?? 0) > 6 && (
                        <span className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-500">
                          +
                          {job.skills!.length - 6}
                        </span>
                      )}
                    </div>
                  )}

                  <div className="mt-6 flex items-center justify-between border-t border-slate-800 pt-5">
                    <div>
                      <p className="text-xs text-slate-500">
                        Salary
                      </p>

                      <p className="mt-1 text-sm font-semibold">
                        {job.salary_text ??
                          (job.min_salary_lpa ||
                          job.max_salary_lpa
                            ? `${job.min_salary_lpa ?? ""}-${job.max_salary_lpa ?? ""} LPA`
                            : "Not specified")}
                      </p>
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          openJob(job)
                        }
                        className="flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold transition hover:bg-slate-800"
                      >
                        Details
                        <ChevronRight className="h-4 w-4" />
                      </button>

                      <button
                        onClick={() =>
                          void handleApply(job)
                        }
                        disabled={
                          applyingJobId ===
                          job.id
                        }
                        className="rounded-lg bg-cyan-500 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50"
                      >
                        {applyingJobId ===
                        job.id
                          ? "Applying..."
                          : "Apply"}
                      </button>
                    </div>
                  </div>

                  {applyMessage &&
                    applyingJobId === null && (
                      <p className="mt-3 text-xs text-cyan-400">
                        {applyMessage}
                      </p>
                    )}
                </div>
              );
            })}
          </div>
        )}

      {selectedJob && (
        <JobModal
          job={selectedJob}
          onClose={() =>
            setSelectedJob(null)
          }
          onMatch={handleMatch}
          onAnalyze={handleAnalyze}
          matching={matching}
          analyzing={analyzing}
          match={match}
          analysis={analysis}
        />
      )}
    </div>
  );
}