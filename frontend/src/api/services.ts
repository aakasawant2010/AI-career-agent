import api from "./client";

/* ============================================================
   TYPES
============================================================ */

export interface CareerProfile {
  id?: string;
  full_name?: string;
  email?: string;
  phone?: string;
  location?: string;
  summary?: string;
  target_roles?: string[];
  skills?: string[];
  technologies?: string[];
  total_experience_years?: number;
}

export interface Project {
  id?: string;
  name: string;
  description?: string;
  technologies?: string[];
  url?: string;
}

export interface Resume {
  id: string;
  filename?: string;
  title?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Job {
  id: string;
  source?: string;
  external_id?: string;

  title: string;
  company: string;
  location?: string;
  work_mode?: string;
  employment_type?: string;

  description?: string;
  requirements?: string;

  skills?: string[];
  technologies?: string[];

  min_salary_lpa?: number;
  max_salary_lpa?: number;
  salary_text?: string;

  experience_min_years?: number;
  experience_max_years?: number;

  notice_period_days?: number;

  apply_url?: string;
  source_url?: string;
  posted_at?: string;

  created_at?: string;
  updated_at?: string;
}

export interface JobMatch {
  id?: string;
  job_id: string;

  score?: number;
  match_score?: number;

  recommendation?: string;

  breakdown?: Record<string, number>;

  matched_skills?: string[];
  missing_skills?: string[];

  risks?: string[];
  risk?: string;

  weights?: Record<string, number>;
}

export interface JobRecommendation extends Job {
  match_score?: number;
  score?: number;
  recommendation?: string;
  matched_skills?: string[];
  missing_skills?: string[];
  risk?: string;
  risks?: string[];
}

export interface Application {
  id: string;
  job_id?: string;

  status: string;
  submission_mode?: string;

  created_at?: string;
  updated_at?: string;

  job?: Job;
}

export interface ApplicationAnalytics {
  total: number;

  by_status: Record<string, number>;

  conversion_rate?: number;
  avg_match_score?: number;

  pending_followups?: number;
  applications_last_30_days?: number;
}

export interface Interview {
  id: string;
  job_id?: string;
  status?: string;
  score?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ApiResponse<T> {
  data: T;
}

/* ============================================================
   AUTH
============================================================ */

export const authApi = {
  login: async (payload: {
    email: string;
    password: string;
  }) => {
    const response = await api.post("/auth/login", payload);
    return response.data;
  },

  register: async (payload: {
    email: string;
    password: string;
    full_name?: string;
  }) => {
    const response = await api.post("/auth/register", payload);
    return response.data;
  },

  me: async () => {
    const response = await api.get("/auth/me");
    return response.data;
  },

  refresh: async () => {
    const response = await api.post("/auth/refresh");
    return response.data;
  },

  logout: async () => {
    const response = await api.post("/auth/logout");
    return response.data;
  },
};

/* ============================================================
   PROFILE
============================================================ */

export const profileApi = {
  get: async (): Promise<CareerProfile> => {
    const response = await api.get("/career-profile");
    return response.data;
  },

  update: async (
    payload: Partial<CareerProfile>
  ): Promise<CareerProfile> => {
    const response = await api.put("/career-profile", payload);
    return response.data;
  },

  getProjects: async (): Promise<Project[]> => {
    const response = await api.get("/projects");

    return Array.isArray(response.data)
      ? response.data
      : response.data?.items ?? response.data?.projects ?? [];
  },

  createProject: async (
    payload: Omit<Project, "id">
  ): Promise<Project> => {
    const response = await api.post("/projects", payload);
    return response.data;
  },
};

/* ============================================================
   RESUME
============================================================ */

export const resumeApi = {
  list: async (): Promise<Resume[]> => {
    const response = await api.get("/resumes");

    return Array.isArray(response.data)
      ? response.data
      : response.data?.items ?? response.data?.resumes ?? [];
  },

  upload: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post("/resumes", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  },

  getIntelligence: async (resumeId: string) => {
    const response = await api.get(
      `/resume-intelligence/${resumeId}`
    );

    return response.data;
  },

  generateIntelligence: async (resumeId: string) => {
    const response = await api.post(
      `/resume-intelligence/${resumeId}/generate`
    );

    return response.data;
  },

  generateCandidateIntelligence: async () => {
    const response = await api.post(
      "/candidate-intelligence/generate"
    );

    return response.data;
  },
};

/* ============================================================
   JOBS
============================================================ */

export const jobsApi = {
  list: async (): Promise<Job[]> => {
    const response = await api.get("/jobs");

    if (Array.isArray(response.data)) {
      return response.data;
    }

    return (
      response.data?.items ??
      response.data?.jobs ??
      response.data?.results ??
      []
    );
  },

  get: async (jobId: string): Promise<Job> => {
    const response = await api.get(`/jobs/${jobId}`);
    return response.data;
  },

  analyze: async (jobId: string) => {
    const response = await api.post(
      `/jobs/${jobId}/analyze`
    );

    return response.data;
  },

  match: async (jobId: string): Promise<JobMatch> => {
    const response = await api.post(
      `/jobs/${jobId}/match`
    );

    return response.data;
  },

  recommendations: async (): Promise<JobRecommendation[]> => {
    const response = await api.get(
      "/jobs/recommendations"
    );

    if (Array.isArray(response.data)) {
      return response.data;
    }

    return (
      response.data?.items ??
      response.data?.jobs ??
      response.data?.recommendations ??
      response.data?.results ??
      []
    );
  },

  import: async (payload: Partial<Job>) => {
    const response = await api.post(
      "/jobs/import",
      payload
    );

    return response.data;
  },
};

/* ============================================================
   APPLICATIONS
============================================================ */

export const applicationsApi = {
  list: async (): Promise<Application[]> => {
    const response = await api.get("/applications");

    if (Array.isArray(response.data)) {
      return response.data;
    }

    return (
      response.data?.items ??
      response.data?.applications ??
      response.data?.results ??
      []
    );
  },

  get: async (
    applicationId: string
  ): Promise<Application> => {
    const response = await api.get(
      `/applications/${applicationId}`
    );

    return response.data;
  },

  create: async (payload: {
    job_id: string;
    submission_mode?: string;
  }) => {
    const response = await api.post(
      "/applications",
      payload
    );

    return response.data;
  },

  prepare: async (applicationId: string) => {
    const response = await api.post(
      `/applications/${applicationId}/prepare`
    );

    return response.data;
  },

  approve: async (applicationId: string) => {
    const response = await api.post(
      `/applications/${applicationId}/approve`
    );

    return response.data;
  },

  submit: async (applicationId: string) => {
    const response = await api.post(
      `/applications/${applicationId}/submit`
    );

    return response.data;
  },

  updateStatus: async (
    applicationId: string,
    status: string,
    note?: string
  ) => {
    const response = await api.post(
      `/applications/${applicationId}/status`,
      {
        status,
        note,
      }
    );

    return response.data;
  },

  getPackage: async (applicationId: string) => {
    const response = await api.get(
      `/applications/${applicationId}/package`
    );

    return response.data;
  },

  getEvents: async (applicationId: string) => {
    const response = await api.get(
      `/applications/${applicationId}/events`
    );

    return Array.isArray(response.data)
      ? response.data
      : response.data?.items ?? response.data?.events ?? [];
  },

  createFollowUp: async (
    applicationId: string,
    payload: Record<string, unknown>
  ) => {
    const response = await api.post(
      `/applications/${applicationId}/follow-ups`,
      payload
    );

    return response.data;
  },

  analytics: async (): Promise<ApplicationAnalytics> => {
    const response = await api.get(
      "/applications/analytics/summary"
    );

    return response.data;
  },
};

/* ============================================================
   INTERVIEWS
============================================================ */

export const interviewApi = {
  create: async (payload: Record<string, unknown>) => {
    const response = await api.post(
      "/interviews",
      payload
    );

    return response.data;
  },

  get: async (interviewId: string) => {
    const response = await api.get(
      `/interviews/${interviewId}`
    );

    return response.data;
  },

  feedback: async (
    interviewId: string,
    payload: Record<string, unknown>
  ) => {
    const response = await api.post(
      `/interviews/${interviewId}/feedback`,
      payload
    );

    return response.data;
  },
};

/* ============================================================
   RAG
============================================================ */

export const ragApi = {
  ingest: async (payload: {
    kind: string;
    title: string;
    text: string;
  }) => {
    const response = await api.post(
      "/rag/documents",
      payload
    );

    return response.data;
  },

  search: async (
    query: string,
    topK = 5
  ) => {
    const response = await api.post(
      "/rag/search",
      {
        query,
        top_k: topK,
      }
    );

    return response.data;
  },
};