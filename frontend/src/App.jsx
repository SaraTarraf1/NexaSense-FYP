
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import Register from "./pages/Register.jsx";
import ProjectPolicy from "./pages/ProjectPolicy.jsx";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/terms" element={<ProjectPolicy type="terms" />} />
        <Route path="/privacy" element={<ProjectPolicy type="privacy" />} />
        <Route
          path="/"
          element={<Navigate to="/register" replace />}
        />

        <Route
          path="/register"
          element={<Register />}
        />

        <Route
          path="*"
          element={<Navigate to="/register" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
