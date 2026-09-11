import { Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import { ProjectDashboard } from "./pages/ProjectDashboard";
import { QueryDownload } from "./pages/QueryDownload";
import { StudyDashboard } from "./pages/StudyDashboard";
import { StudyList } from "./pages/StudyList";

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<ProjectDashboard />} />
        <Route path="studies" element={<StudyList />} />
        <Route path="studies/:studyId" element={<StudyDashboard />} />
        <Route path="query" element={<QueryDownload />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
