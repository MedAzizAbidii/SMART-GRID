import { Routes, Route } from "react-router-dom";
import AppShell from "./components/layout/AppShell";
import Dashboard from "./pages/Dashboard";
import SmartGrid from "./pages/SmartGrid";
import AIDetection from "./pages/AIDetection";
import ExplainableAI from "./pages/ExplainableAI";
import Blockchain from "./pages/Blockchain";
import Operations from "./pages/Operations";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/smart-grid" element={<SmartGrid />} />
        <Route path="/smart-meters" element={<Operations page="meters" />} />
        <Route path="/ai-detection" element={<AIDetection />} />
        <Route path="/explainable-ai" element={<ExplainableAI />} />
        <Route path="/cybersecurity" element={<Operations page="security" />} />
        <Route path="/electricity-theft" element={<Operations page="theft" />} />
        <Route path="/blockchain" element={<Blockchain />} />
        <Route path="/analytics" element={<Operations page="analytics" />} />
        <Route path="/alerts" element={<Operations page="alerts" />} />
        <Route path="/performance" element={<Operations page="performance" />} />
        <Route path="/reports" element={<Operations page="reports" />} />
        <Route path="/users" element={<Operations page="users" />} />
        <Route path="/settings" element={<Operations page="settings" />} />
      </Route>
    </Routes>
  );
}
