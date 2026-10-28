import {
  Activity,
  BriefcaseBusiness,
  CheckCircle2,
  Clock3,
  FileText,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  applicationsApi,
  jobsApi,
  type Application,
  type Job,
} from "../api/services";

type JobWithScore = Job & {
  match_score?: number;
  score?: number;
};

function getScore(job: JobWithScore) {
  return job.match_score ?? job.score ?? 0;
}

function StatCard({
  title,
  value,
  subtitle,
  icon,
}: {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-400">{title}</p>

          <p className="mt-3 text-3xl font-bold">
            {value}
          </p>

          <p className="mt-2 text-xs text-slate-500">
            {subtitle}
          </p>
        </div>

        <div className="rounded-xl bg-cyan-500/10 p-3 text-cyan-400">
          {icon}
        </div>
      </div>
    </div>
  );
}

function PipelineCard({
  title,
  count,
}: {
  title: string;
  count: number;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
      <p className="text-xs text-slate-500">
        {title}
      </p>

      <p className="mt-2 text-2xl font-bold">
        {count}
      </p>
    </div>
  );
}

export default function Dashboard() {
  const [jobs, setJobs] = useState<JobWithScore[]>([]);
  const [applications, setApplications] =
    useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        setLoading(true);
        setError("");

        const [
          jobsResponse,
          applicationsResponse,
        ] = await Promise.all([
          jobsApi.list(),
          applicationsApi.list(),
        ]);

        setJobs(jobsResponse ?? []);
        setApplications(
          Array.isArray(applicationsResponse)
            ? applicationsResponse
            : []
        );
      } catch (err: any) {
        setError(
          err?.response?.data?.detail ??
            "Unable to load dashboard data."
        );
      } finally {
        setLoading(false);
      }
    };

    void loadDashboard();
  }, []);

  const averageMatchScore = useMemo(() => {
    const scores = jobs
      .map(getScore)
      .filter((score) => score > 0);

    if (scores.length === 0) {
      return 0;
    }

    return Math.round(
      scores.reduce(
        (total, score) => total + score,
        0
      ) / scores.length
    );
  }, [jobs]);

  const pipeline = useMemo(() => {
    return {
      draft: applications.filter(
        (app) => app.status === "DRAFT"
      ).length,

      prepared: applications.filter(
        (app) => app.status === "PREPARED"
      ).length,

      pendingApproval: applications.filter(
        (app) =>
          app.status === "PENDING_APPROVAL"
      ).length,

      submitted: applications.filter(
        (app) =>
          app.status === "SUBMITTED"
      ).length,

      rejected: applications.filter(
        (app) =>
          app.status === "REJECTED"
      ).length,
    };
  }, [applications]);

  const recentApplications = useMemo(() => {
    return [...applications]
      .reverse()
      .slice(0, 5);
  }, [applications]);

  if (loading) {
    return (
      <div className="space-y-8">
        <div>
          <div className="h-8 w-48 animate-pulse rounded bg-slate-800" />

          <div className="mt-3 h-4 w-80 animate-pulse rounded bg-slate-800" />
        </div>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map(
            (_, index) => (
              <div
                key={index}
                className="h-36 animate-pulse rounded-2xl bg-slate-900"
              />
            )
          )}
        </div>

        <div className="h-64 animate-pulse rounded-2xl bg-slate-900" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center gap-3">
          <TrendingUp className="h-7 w-7 text-cyan-400" />

          <h1 className="text-3xl font-bold">
            Career Dashboard
          </h1>
        </div>

        <p className="mt-2 text-slate-400">
          Your AI-powered job search and application
          overview.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-300">
          {error}
        </div>
      )}

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Applications"
          value={applications.length}
          subtitle="Total applications"
          icon={
            <FileText className="h-5 w-5" />
          }
        />

        <StatCard
          title="Jobs Matched"
          value={jobs.length}
          subtitle="Available opportunities"
          icon={
            <BriefcaseBusiness className="h-5 w-5" />
          }
        />

        <StatCard
          title="Avg Match Score"
          value={`${averageMatchScore}%`}
          subtitle="Across matched jobs"
          icon={
            <Target className="h-5 w-5" />
          }
        />

        <StatCard
          title="Submitted"
          value={pipeline.submitted}
          subtitle="Applications submitted"
          icon={
            <CheckCircle2 className="h-5 w-5" />
          }
        />
      </div>

      <section>
        <div className="mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5 text-cyan-400" />

          <h2 className="text-xl font-bold">
            Application Pipeline
          </h2>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <PipelineCard
            title="Draft"
            count={pipeline.draft}
          />

          <PipelineCard
            title="Prepared"
            count={pipeline.prepared}
          />

          <PipelineCard
            title="Pending Approval"
            count={pipeline.pendingApproval}
          />

          <PipelineCard
            title="Submitted"
            count={pipeline.submitted}
          />

          <PipelineCard
            title="Rejected"
            count={pipeline.rejected}
          />
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-center gap-2">
            <BriefcaseBusiness className="h-5 w-5 text-cyan-400" />

            <h2 className="text-lg font-bold">
              Top Job Matches
            </h2>
          </div>

          <div className="mt-5 space-y-3">
            {[...jobs]
              .sort(
                (a, b) =>
                  getScore(b) -
                  getScore(a)
              )
              .slice(0, 5)
              .map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950 p-4"
                >
                  <div className="min-w-0">
                    <p className="truncate font-semibold">
                      {job.title}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {job.company}
                    </p>
                  </div>

                  <div className="ml-4 rounded-full bg-cyan-500/10 px-3 py-1 text-sm font-bold text-cyan-400">
                    {Math.round(
                      getScore(job)
                    )}
                    %
                  </div>
                </div>
              ))}

            {jobs.length === 0 && (
              <div className="py-10 text-center text-sm text-slate-500">
                No jobs available yet.
              </div>
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-center gap-2">
            <Clock3 className="h-5 w-5 text-cyan-400" />

            <h2 className="text-lg font-bold">
              Recent Applications
            </h2>
          </div>

          <div className="mt-5 space-y-3">
            {recentApplications.map(
              (application) => (
                <div
                  key={application.id}
                  className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950 p-4"
                >
                  <div>
                    <p className="font-semibold">
                      Job Application
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      Job ID:{" "}
                      {application.job_id ??
                        "Unknown"}
                    </p>
                  </div>

                  <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-medium text-slate-300">
                    {application.status}
                  </span>
                </div>
              )
            )}

            {recentApplications.length ===
              0 && (
              <div className="py-10 text-center text-sm text-slate-500">
                No applications yet.
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-slate-800 bg-gradient-to-r from-cyan-500/10 to-slate-900 p-6">
        <div className="flex items-center gap-4">
          <div className="rounded-xl bg-cyan-500/10 p-3 text-cyan-400">
            <Users className="h-6 w-6" />
          </div>

          <div>
            <h2 className="font-bold">
              AI Career Agent
            </h2>

            <p className="mt-1 text-sm text-slate-400">
              Your job discovery, matching and
              application pipeline are connected to
              the backend.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}