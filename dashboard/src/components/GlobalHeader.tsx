import { useLocation } from "react-router-dom";
import ProjectSelector from "./ProjectSelector.tsx";
import { useProject } from "../context/ProjectContext.tsx";

const PAGE_TITLES: Record<string, string> = {
  "/": "Overview",
  "/remember": "Remember",
  "/setup": "Setup",
  "/memories": "Memories",
  "/graph": "Graph",
  "/monitoring": "Monitoring",
  "/guide": "Guide",
};

export default function GlobalHeader() {
  const { pathname } = useLocation();
  const { project, setProject } = useProject();
  const title = PAGE_TITLES[pathname] ?? "";

  // Guide doesn't need project filter
  const showSelector = pathname !== "/guide";

  return (
    <header className="shrink-0 flex items-center justify-between px-6 h-12 border-b border-slate-800 bg-slate-900/80">
      <h1 className="text-xl font-bold text-white">{title}</h1>
      {showSelector && (
        <ProjectSelector value={project} onChange={setProject} />
      )}
    </header>
  );
}
