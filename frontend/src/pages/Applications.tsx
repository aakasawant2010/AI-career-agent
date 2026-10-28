import { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Clock3,
  FileText,
  RefreshCw,
  Send,
  X,
  XCircle,
} from "lucide-react";

import {
  applicationsApi,
  type Application,
} from "../api/services";

const statusConfig: Record<
  string,
  {
    label: string;
    icon: typeof FileText;
    className: string;
  }
> = {
  DRAFT: {
    label: "Draft",
    icon: FileText,
    className: "text-slate-300 bg-slate-800",
  },

  PREPARED: {
    label: "Prepared",
    icon: Clock3,
    className: "text-cyan-300 bg-cyan-400/10",
  },

  PENDING_APPROVAL: {
    label: "Pending Approval",
    icon: Clock3,
    className: "text-yellow-300 bg-yellow-400/10",
  },

  APPROVED: {
    label: "Approved",
    icon: CheckCircle2,
    className: "text-emerald-300 bg-emerald-400/10",
  },

  SUBMITTED: {
    label: "Submitted",
    icon: Send,
    className: "text-indigo-300 bg-indigo-400/10",
  },

  REJECTED: {
    label: "Rejected",
    icon: XCircle,
    className: "text-red-300 bg-red-400/10",
  },
};

function StatusBadge({
  status,
}: {
  status: string;
}) {
  const config =
    statusConfig[status] ??
    statusConfig.DRAFT;

  const Icon = config.icon;

  return (
    <div
      className={`flex w-fit items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${config.className}`}
    >
      <Icon className="h-4 w-4" />

      {config.label}
    </div>
  );
}

function StatCard({
  label,
  count,
}: {
  label: string;
  count: number;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
      <p className="text-sm text-slate-400">
        {label}
      </p>

      <p className="mt-3 text-3xl font-bold">
        {count}
      </p>
    </div>
  );
}

export default function Applications() {
  const [applications, setApplications] =
    useState<Application[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] =
    useState("");

  const [filter, setFilter] =
    useState("ALL");

  const [selectedApplication, setSelectedApplication] =
    useState<Application | null>(null);

  async function loadApplications(
    isRefresh = false
  ) {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const response =
        await applicationsApi.list();

      setApplications(
        Array.isArray(response)
          ? response
          : []
      );
    } catch (err) {
      console.error(err);

      setError(
        "Unable to load applications."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadApplications();
  }, []);

  const counts = useMemo(() => {
    return {
      all: applications.length,

      draft: applications.filter(
        (application) =>
          application.status === "DRAFT"
      ).length,

      prepared: applications.filter(
        (application) =>
          application.status === "PREPARED"
      ).length,

      pending: applications.filter(
        (application) =>
          application.status ===
          "PENDING_APPROVAL"
      ).length,

      approved: applications.filter(
        (application) =>
          application.status === "APPROVED"
      ).length,

      submitted: applications.filter(
        (application) =>
          application.status === "SUBMITTED"
      ).length,

      rejected: applications.filter(
        (application) =>
          application.status === "REJECTED"
      ).length,
    };
  }, [applications]);

  const filteredApplications = useMemo(() => {
    if (filter === "ALL") {
      return applications;
    }

    return applications.filter(
      (application) =>
        application.status === filter
    );
  }, [applications, filter]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-3xl font-bold">
            Applications
          </h2>

          <p className="mt-2 text-slate-400">
            Track your applications from
            preparation to submission.
          </p>
        </div>

        <button
          onClick={() =>
            void loadApplications(true)
          }
          disabled={refreshing}
          className="flex w-fit items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm font-medium transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${
              refreshing
                ? "animate-spin"
                : ""
            }`}
          />

          {refreshing
            ? "Refreshing..."
            : "Refresh"}
        </button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Applications"
          count={counts.all}
        />

        <StatCard
          label="Draft"
          count={counts.draft}
        />

        <StatCard
          label="Pending Approval"
          count={counts.pending}
        />

        <StatCard
          label="Submitted"
          count={counts.submitted}
        />
      </div>

      {/* Pipeline */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
        <div className="mb-4">
          <h3 className="font-semibold">
            Application Pipeline
          </h3>

          <p className="mt-1 text-xs text-slate-500">
            Current state of your applications.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
          {[
            {
              key: "ALL",
              label: "All",
              count: counts.all,
            },
            {
              key: "DRAFT",
              label: "Draft",
              count: counts.draft,
            },
            {
              key: "PREPARED",
              label: "Prepared",
              count: counts.prepared,
            },
            {
              key: "PENDING_APPROVAL",
              label: "Pending",
              count: counts.pending,
            },
            {
              key: "APPROVED",
              label: "Approved",
              count: counts.approved,
            },
            {
              key: "SUBMITTED",
              label: "Submitted",
              count: counts.submitted,
            },
          ].map((item) => (
            <button
              key={item.key}
              onClick={() =>
                setFilter(item.key)
              }
              className={`rounded-xl border p-3 text-left transition ${
                filter === item.key
                  ? "border-cyan-500/40 bg-cyan-500/10"
                  : "border-slate-800 bg-slate-950 hover:border-slate-700"
              }`}
            >
              <p className="text-xs text-slate-500">
                {item.label}
              </p>

              <p className="mt-1 text-xl font-bold">
                {item.count}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map(
            (_, index) => (
              <div
                key={index}
                className="h-32 animate-pulse rounded-2xl bg-slate-900"
              />
            )
          )}
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6 text-red-300">
          <p>{error}</p>

          <button
            onClick={() =>
              void loadApplications()
            }
            className="mt-4 rounded-lg bg-red-500/10 px-4 py-2 text-sm hover:bg-red-500/20"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Empty */}
      {!loading &&
        !error &&
        filteredApplications.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900 p-14 text-center">
            <FileText className="mx-auto h-10 w-10 text-slate-600" />

            <h3 className="mt-4 text-lg font-semibold">
              {applications.length === 0
                ? "No applications yet"
                : "No applications in this status"}
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              {applications.length === 0
                ? "Apply to a job from the Jobs section to start tracking it here."
                : "Try selecting another application status."}
            </p>
          </div>
        )}

      {/* Applications */}
      {!loading &&
        !error &&
        filteredApplications.length > 0 && (
          <div className="space-y-4">
            {filteredApplications.map(
              (application) => (
                <div
                  key={application.id}
                  className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 transition hover:border-slate-700 hover:bg-slate-900"
                >
                  <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <p className="text-xs uppercase tracking-wider text-slate-500">
                          Application
                        </p>

                        <StatusBadge
                          status={
                            application.status
                          }
                        />
                      </div>

                      <h3 className="mt-3 truncate font-semibold">
                        {application.id}
                      </h3>

                      <p className="mt-2 text-sm text-slate-500">
                        Job ID:{" "}
                        {application.job_id ??
                          "Unknown"}
                      </p>

                      {application.submission_mode && (
                        <p className="mt-1 text-xs text-slate-600">
                          Submission mode:{" "}
                          {
                            application.submission_mode
                          }
                        </p>
                      )}
                    </div>

                    <button
                      onClick={() =>
                        setSelectedApplication(
                          application
                        )
                      }
                      className="w-fit rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-medium transition hover:bg-slate-800"
                    >
                      View Details
                    </button>
                  </div>
                </div>
              )
            )}
          </div>
        )}

      {/* Details Modal */}
      {selectedApplication && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-800 p-6">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500">
                  Application Details
                </p>

                <h2 className="mt-2 text-xl font-bold">
                  {selectedApplication.id}
                </h2>
              </div>

              <button
                onClick={() =>
                  setSelectedApplication(
                    null
                  )
                }
                className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="space-y-6 p-6">
              <div>
                <p className="text-sm text-slate-500">
                  Current Status
                </p>

                <div className="mt-3">
                  <StatusBadge
                    status={
                      selectedApplication.status
                    }
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs text-slate-500">
                    Job ID
                  </p>

                  <p className="mt-2 break-all text-sm font-medium">
                    {selectedApplication.job_id ??
                      "Unknown"}
                  </p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs text-slate-500">
                    Submission Mode
                  </p>

                  <p className="mt-2 text-sm font-medium">
                    {selectedApplication.submission_mode ??
                      "Not specified"}
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-cyan-500/10 bg-cyan-500/5 p-5">
                <div className="flex items-center gap-3">
                  <Clock3 className="h-5 w-5 text-cyan-400" />

                  <div>
                    <p className="font-semibold">
                      Application State
                    </p>

                    <p className="mt-1 text-sm text-slate-400">
                      Your application is currently
                      in the{" "}
                      <span className="font-medium text-cyan-400">
                        {
                          statusConfig[
                            selectedApplication
                              .status
                          ]?.label ??
                            selectedApplication.status
                        }
                      </span>{" "}
                      state.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex justify-end border-t border-slate-800 pt-5">
                <button
                  onClick={() =>
                    setSelectedApplication(
                      null
                    )
                  }
                  className="rounded-xl bg-slate-800 px-5 py-2.5 text-sm font-medium transition hover:bg-slate-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}