import { createContext, useContext, useState, type ReactNode } from "react";

interface ProjectContextType {
  project: string;
  setProject: (p: string) => void;
}

const ProjectContext = createContext<ProjectContextType>({
  project: "",
  setProject: () => {},
});

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [project, setProject] = useState("");
  return (
    <ProjectContext.Provider value={{ project, setProject }}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  return useContext(ProjectContext);
}
