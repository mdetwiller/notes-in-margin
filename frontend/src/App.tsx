import { NavLink, Route, Routes } from "react-router-dom";
import ReaderPage from "./pages/ReaderPage";
import MemoPage from "./pages/MemoPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <>
      <nav className="topnav">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Reader
        </NavLink>
        <NavLink to="/memo" className={({ isActive }) => (isActive ? "active" : "")}>
          Memo
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => (isActive ? "active" : "")}>
          Settings
        </NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<ReaderPage />} />
        <Route path="/memo" element={<MemoPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </>
  );
}
