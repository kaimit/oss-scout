import reportsData from "@/data/reports.json";

export type Proposal = {
  title: string;
  strategy: string;
  type: string;
  impact: number;
  effort: string;
  rationale: string;
  evidence: string;
};

export type Report = {
  meta: { stars?: number; license_spdx?: string; description?: string };
  license_policy?: { spdx: string; notes: string[] };
  proposals: Proposal[];
  assessment_excerpt: string;
};

const data = reportsData as {
  generated_at?: string;
  reports?: Record<string, Report>;
};

export const reports: Record<string, Report> = data.reports || {};
export const reportsGeneratedAt: string = data.generated_at || "";
