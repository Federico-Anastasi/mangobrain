import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar.tsx";
import Overview from "./pages/Overview.tsx";
import Memories from "./pages/Memories.tsx";
import Graph from "./pages/Graph.tsx";
import Monitoring from "./pages/Monitoring.tsx";
import Setup from "./pages/Setup.tsx";
import Guide from "./pages/Guide.tsx";

function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-slate-900 text-slate-200">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/memories" element={<Memories />} />
            <Route path="/graph" element={<Graph />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/setup" element={<Setup />} />
            <Route path="/guide" element={<Guide />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
