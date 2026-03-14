import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ProjectProvider } from "./context/ProjectContext.tsx";
import Sidebar from "./components/Sidebar.tsx";
import GlobalHeader from "./components/GlobalHeader.tsx";
import Overview from "./pages/Overview.tsx";
import Memories from "./pages/Memories.tsx";
import Graph from "./pages/Graph.tsx";
import Monitoring from "./pages/Monitoring.tsx";
import Setup from "./pages/Setup.tsx";
import Guide from "./pages/Guide.tsx";
import Remember from "./pages/Remember.tsx";

function App() {
  return (
    <BrowserRouter>
      <ProjectProvider>
        <div className="flex h-screen bg-slate-900 text-slate-200">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <GlobalHeader />
            <main className="flex-1 overflow-y-auto p-6">
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/remember" element={<Remember />} />
                <Route path="/memories" element={<Memories />} />
                <Route path="/graph" element={<Graph />} />
                <Route path="/monitoring" element={<Monitoring />} />
                <Route path="/setup" element={<Setup />} />
                <Route path="/guide" element={<Guide />} />
              </Routes>
            </main>
          </div>
        </div>
      </ProjectProvider>
    </BrowserRouter>
  );
}

export default App;
