// GitHub search 最多 5 个逻辑操作符 → 6 个关键词（5 个 OR）为上限
const AGENT_QUERY =
  "agent OR agentic OR llm OR autonomous OR rag OR mcp in:name,description";

export type Candidate = {
  repo: string;
  description: string;
  language: string;
  stars: number;
  url: string;
  topics: string[];
};

export async function searchAgents(
  days = 90,
  minStars = 100,
  perPage = 30,
): Promise<Candidate[]> {
  const since = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
  const q = `${AGENT_QUERY} pushed:>${since} stars:>=${minStars}`;
  const url =
    "https://api.github.com/search/repositories?q=" +
    encodeURIComponent(q) +
    `&sort=stars&order=desc&per_page=${perPage}`;

  const headers: Record<string, string> = {
    Accept: "application/vnd.github+json",
    "User-Agent": "oss-scout-web",
    "X-GitHub-Api-Version": "2022-11-28",
  };
  if (process.env.GITHUB_TOKEN) {
    headers.Authorization = "Bearer " + process.env.GITHUB_TOKEN;
  }

  // ISR：30 分钟内复用结果，避免每次请求都打 GitHub API
  const r = await fetch(url, { headers, next: { revalidate: 1800 } });
  if (!r.ok) {
    throw new Error(`GitHub API ${r.status}`);
  }
  const d = await r.json();
  return (d.items || []).map(
    (it: {
      full_name: string;
      description: string | null;
      language: string | null;
      stargazers_count: number;
      html_url: string;
      topics?: string[];
    }): Candidate => ({
      repo: it.full_name,
      description: it.description || "",
      language: it.language || "",
      stars: it.stargazers_count || 0,
      url: it.html_url,
      topics: it.topics || [],
    }),
  );
}
