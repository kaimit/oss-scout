"use client";

import { useEffect, useState } from "react";
import { reports, reportsGeneratedAt, type Report } from "@/lib/reports";

type Candidate = {
  repo: string;
  description: string;
  language: string;
  stars: number;
  url: string;
  topics: string[];
};

function Proposals({ report }: { report: Report }) {
  return (
    <div className="proposals">
      {(report.proposals || []).map((p, i) => (
        <div key={i} className="prop">
          <div className="prop-h">
            <strong>{p.title}</strong>
            <span className={`strat ${p.strategy}`}>{p.strategy}</span>
          </div>
          <div className="prop-meta">
            {p.type} · 影响 {p.impact}/5 · 工作量 {p.effort} · 证据 {p.evidence}
          </div>
          <p className="prop-r">{p.rationale}</p>
        </div>
      ))}
    </div>
  );
}

export default function Home() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/discover")
      .then((r) => r.json())
      .then((d) => {
        setCandidates(d.items || []);
        if (d.error) setError(d.error);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem("oss-scout-selected");
    if (saved) setSelected(JSON.parse(saved));
  }, []);

  function toggle(repo: string) {
    setSelected((prev) => {
      const next = prev.includes(repo)
        ? prev.filter((r) => r !== repo)
        : [...prev, repo];
      localStorage.setItem("oss-scout-selected", JSON.stringify(next));
      return next;
    });
  }

  const reportRepos = Object.keys(reports);

  return (
    <main>
      <header className="hero">
        <h1>oss-scout</h1>
        <p>发现 AI agent 领域的开源项目 · 审阅优化提案 · 确认后回本地执行</p>
        <div className="flow">
          <span>发现</span>
          <i>→</i>
          <span>审阅</span>
          <i>→</i>
          <span className="hl">你确认</span>
          <i>→</i>
          <span>本地优化 (Claude Code)</span>
          <i>→</i>
          <span>人工发布</span>
        </div>
      </header>

      {selected.length > 0 && (
        <section className="tray">
          <h2>已选 {selected.length} 个 · 下一步在本地执行</h2>
          <pre>
            {selected
              .map((r) => `oss-scout analyze ${r} && oss-scout propose ${r}`)
              .join("\n")}
          </pre>
          <button
            onClick={() => {
              setSelected([]);
              localStorage.removeItem("oss-scout-selected");
            }}
          >
            清空选择
          </button>
        </section>
      )}

      <section>
        <h2 className="sec">
          🔥 Agent 领域候选{loading ? "（加载中…）" : `（${candidates.length}）`}
        </h2>
        {error && (
          <p className="err">
            GitHub 拉取受限：{error}（在 Vercel 配 GITHUB_TOKEN 环境变量可提额度）
          </p>
        )}
        <div className="grid">
          {candidates.map((c) => {
            const hasReport = !!reports[c.repo];
            const isSel = selected.includes(c.repo);
            return (
              <div key={c.repo} className={`card ${isSel ? "sel" : ""}`}>
                <div className="card-top">
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                    className="repo"
                  >
                    {c.repo}
                  </a>
                  <span className="stars">★ {c.stars.toLocaleString()}</span>
                </div>
                <p className="desc">{c.description}</p>
                <div className="tags">
                  {c.language && <span className="tag lang">{c.language}</span>}
                  {c.topics.slice(0, 3).map((t) => (
                    <span key={t} className="tag">
                      {t}
                    </span>
                  ))}
                  {hasReport && <span className="tag done">已分析</span>}
                </div>
                <div className="card-actions">
                  <label className="pick">
                    <input
                      type="checkbox"
                      checked={isSel}
                      onChange={() => toggle(c.repo)}
                    />
                    选中优化
                  </label>
                  {hasReport && (
                    <button
                      className="link"
                      onClick={() =>
                        setExpanded(expanded === c.repo ? null : c.repo)
                      }
                    >
                      {expanded === c.repo ? "收起提案" : "看提案"}
                    </button>
                  )}
                </div>
                {expanded === c.repo && hasReport && (
                  <Proposals report={reports[c.repo]} />
                )}
              </div>
            );
          })}
        </div>
      </section>

      {reportRepos.length > 0 && (
        <section>
          <h2 className="sec">
            📋 已生成分析（本地导出
            {reportsGeneratedAt ? " · " + reportsGeneratedAt.slice(0, 10) : ""}）
          </h2>
          <div className="grid">
            {reportRepos.map((repo) => (
              <div key={repo} className="card">
                <div className="card-top">
                  <a
                    href={`https://github.com/${repo}`}
                    target="_blank"
                    rel="noreferrer"
                    className="repo"
                  >
                    {repo}
                  </a>
                  <span className="stars">
                    {reports[repo].license_policy?.spdx || ""}
                  </span>
                </div>
                <Proposals report={reports[repo]} />
              </div>
            ))}
          </div>
        </section>
      )}

      <footer>
        实际优化由本地 Claude Code 执行、你 review；PR 与 X 帖子人工核对后手动发布。
        这是有意保留的人工把关，避免 AI slop。
      </footer>
    </main>
  );
}
