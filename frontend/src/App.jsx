import { useEffect, useMemo, useState } from "react";

const REFRESH_MS = 30000;

function ProjectCard({ p, index }) {
  return (
    <article className="card" style={{ animationDelay: `${index * 90}ms` }}>
      <div className="cardTop">
        <h3>{p.name}</h3>
        <span className="score">Score {p.score}</span>
      </div>
      <p className="desc">{p.short_description}</p>
      <div className="metaRow">
        <span>{p.category}</span>
        <span>{p.language || "N/A"}</span>
        <span>Stars {p.stars || 0}</span>
      </div>
      <div className="tags">
        {(p.tech_stack || []).map((t) => (
          <span key={t} className="tag">
            {t}
          </span>
        ))}
      </div>
      <a
        className="repoLink"
        href={p.html_url}
        target="_blank"
        rel="noreferrer"
      >
        Open Repository
      </a>
    </article>
  );
}

export default function App() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState("");

  const totalStars = useMemo(
    () => projects.reduce((sum, p) => sum + (p.stars || 0), 0),
    [projects],
  );

  async function loadProjects() {
    try {
      setError("");
      const res = await fetch("/api/projects");
      if (!res.ok) {
        throw new Error(`API returned ${res.status}`);
      }
      const data = await res.json();
      setProjects(data.projects || []);
      setUpdatedAt(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err.message || "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProjects();
    const t = setInterval(loadProjects, REFRESH_MS);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="page">
      <header className="hero">
        <p className="eyebrow">Live AI Portfolio</p>
        <h1>Projects that update themselves</h1>
        <p className="sub">
          New pushes trigger analysis, AI summaries, and ranking. Your portfolio
          reflects the latest best work automatically.
        </p>
        <div className="stats">
          <div>
            <strong>{projects.length}</strong>
            <span>Featured Projects</span>
          </div>
          <div>
            <strong>{totalStars}</strong>
            <span>Total Stars</span>
          </div>
          <div>
            <strong>{updatedAt || "-"}</strong>
            <span>Last Sync</span>
          </div>
        </div>
      </header>

      {loading ? <p className="state">Loading projects...</p> : null}
      {error ? <p className="state error">{error}</p> : null}

      <main className="grid">
        {projects.map((p, i) => (
          <ProjectCard key={p.id || p.repo_id || p.full_name} p={p} index={i} />
        ))}
      </main>
    </div>
  );
}
