import { StrictMode } from "react";
import type { ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import "./index.css";
import StudentLayout from "./components/StudentLayout";
import TeacherLayout from "./components/TeacherLayout";
import { SessionProvider, useSession } from "./lib/session";
import HomePage from "./student/HomePage";
import LibraryPage from "./student/LibraryPage";
import NotesPage from "./student/NotesPage";
import ProgressPage from "./student/ProgressPage";
import SessionPage from "./student/SessionPage";
import ClassesPage from "./teacher/ClassesPage";
import DashboardPage from "./teacher/DashboardPage";
import ReviewQueuePage from "./teacher/ReviewQueuePage";
import SettingsPage from "./teacher/SettingsPage";
import StudentDetailPage from "./teacher/StudentDetailPage";

function Gate({ children }: { children: ReactNode }) {
  const { loading, error } = useSession();
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-xl text-center font-body-lg text-on-surface-variant">
        {error}
      </div>
    );
  }
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center font-body-lg text-on-surface-variant">
        Lade …
      </div>
    );
  }
  return <>{children}</>;
}

const root = document.getElementById("root");
if (!root) {
  throw new Error("root element missing");
}

createRoot(root).render(
  <StrictMode>
    <SessionProvider>
      <BrowserRouter>
        <Gate>
          <Routes>
            <Route element={<StudentLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/lernen" element={<SessionPage />} />
              <Route path="/fortschritt" element={<ProgressPage />} />
              <Route path="/bibliothek" element={<LibraryPage />} />
              <Route path="/notizen" element={<NotesPage />} />
            </Route>
            <Route element={<TeacherLayout />}>
              <Route path="/teacher" element={<DashboardPage />} />
              <Route path="/teacher/classes" element={<ClassesPage />} />
              <Route path="/teacher/student/:id" element={<StudentDetailPage />} />
              <Route path="/teacher/review" element={<ReviewQueuePage />} />
              <Route path="/teacher/settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Gate>
      </BrowserRouter>
    </SessionProvider>
  </StrictMode>,
);
