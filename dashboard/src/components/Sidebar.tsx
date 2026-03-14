import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Database,
  GitFork,
  Activity,
  Brain,
  Rocket,
  BookOpen,
  Search,
} from "lucide-react";

const links = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/remember", label: "Remember", icon: Search },
  { to: "/setup", label: "Setup", icon: Rocket },
  { to: "/memories", label: "Memories", icon: Database },
  { to: "/graph", label: "Graph", icon: GitFork },
  { to: "/monitoring", label: "Monitoring", icon: Activity },
  { to: "/guide", label: "Guide", icon: BookOpen },
];

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 bg-slate-950 border-r border-slate-800 flex flex-col">
      <div className="p-4 flex items-center gap-2 border-b border-slate-800">
        <Brain className="w-6 h-6 text-purple-400" />
        <div>
          <span className="text-lg font-semibold text-white">MangoBrain</span>
          <span className="text-[10px] text-slate-500 ml-1.5">v3</span>
        </div>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`
            }
          >
            <l.icon className="w-4 h-4" />
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="p-3 border-t border-slate-800">
        <p className="text-[10px] text-slate-600 text-center">
          Memory + Workflow System
        </p>
      </div>
    </aside>
  );
}
