import { createContext, useContext, useCallback, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";

interface ProjectContextType {
  project: string;
  setProject: (p: string) => void;
}

const ProjectContext = createContext<ProjectContextType>({
  project: "",
  setProject: () => {},
});

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const project = searchParams.get("project") ?? "";

  const setProject = useCallback(
    (p: string) => {
      setSearchParams(
        (prev) => {
          if (p) {
            prev.set("project", p);
          } else {
            prev.delete("project");
          }
          return prev;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  return (
    <ProjectContext.Provider value={{ project, setProject }}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  return useContext(ProjectContext);
}
