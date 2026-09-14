import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { usePolling } from "../../hooks/usePolling";
import { getHealthDetailed, getModelStatus, getBlockchainStatus, getAlerts } from "../../api/client";
import "./AppShell.css";

export default function AppShell() {
  const health = usePolling(getHealthDetailed, 8000);
  const model = usePolling(getModelStatus, 10000);
  const chain = usePolling(getBlockchainStatus, 10000);
  const alerts = usePolling(getAlerts, 6000);

  const connected = !!health.data && !health.error;
  const systemStatus = connected ? (health.data?.status === "ok" ? "ok" : "degraded") : "down";
  const aiRunning = !!model.data?.detector?.loaded;
  const chainVerified = !!chain.data?.valid;

  return (
    <div className="app-shell">
      <Sidebar systemStatus={systemStatus} />
      <div className="app-shell-main">
        <Topbar
          connected={connected}
          gridOk={connected}
          aiRunning={aiRunning}
          chainVerified={chainVerified}
          alertCount={alerts.data?.count || 0}
        />
        <main className="app-shell-content">
          <Outlet context={{ connected, health: health.data, model: model.data, chain: chain.data, alerts: alerts.data }} />
        </main>
      </div>
    </div>
  );
}
