import { getSession } from "./auth";
import SessionScreen from "./student/SessionScreen";
import Dashboard from "./teacher/Dashboard";

// Minimal role-based routing (/teacher vs everything else). The two views are two
// presentations of the same truth: calm one-concept student session vs dense oversight.
export default function App() {
  const { role } = getSession();
  return role === "teacher" ? <Dashboard /> : <SessionScreen />;
}
