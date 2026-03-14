import { useProjects } from "../hooks/useApi.ts";

interface Props {
  value: string;
  onChange: (v: string) => void;
}

export default function ProjectSelector({ value, onChange }: Props) {
  const { data } = useProjects();
  const projects = data?.projects ?? [];

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-purple-500"
    >
      <option value="">All Projects</option>
      {projects.map((p) => (
        <option key={p.name} value={p.name}>
          {p.name} ({p.count})
        </option>
      ))}
    </select>
  );
}
