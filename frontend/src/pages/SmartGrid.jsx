import { useState } from "react";
import { Card } from "../components/ui/Card";
import { Badge, StatusDot } from "../components/ui/Badge";
import { DataTable } from "../components/ui/DataTable";
import { GridNetwork } from "../components/grid/GridNetwork";
import { usePolling } from "../hooks/usePolling";
import { getGridAll } from "../api/client";

export default function SmartGrid() {
  const { data, error } = usePolling(getGridAll, 2000);
  const [selectedBus, setSelectedBus] = useState(null);

  const buses = data?.buses || [];

  return (
    <div>
      <div className="page-header">
        <div className="page-header-title">
          <h1 className="type-h2">Smart Grid — Live Network</h1>
          <Badge tone={error ? "critical" : "success"}>
            <StatusDot tone={error ? "critical" : "success"} /> {error ? "Offline" : "Streaming · 2s interval"}
          </Badge>
        </div>
        <p className="text-secondary type-small" style={{ marginTop: 4 }}>
          Real-time electrical state from the 14-smart-meter grid simulator (api_server.py `/api/grid/all`)
        </p>
      </div>

      <Card title="Interactive Grid Map" style={{ marginBottom: "var(--space-4)" }}>
        {error ? (
          <div className="empty-state"><div className="empty-state-title">Grid feed unavailable — check api_server.py is running</div></div>
        ) : (
          <GridNetwork buses={buses} height={420} onSelect={setSelectedBus} selectedId={selectedBus?.bus_id} />
        )}
      </Card>

      <Card title="All Smart Meters" subtitle={`${buses.length} monitored`}>
        <DataTable
          emptyMessage="No smart meter data — grid simulator may not be running"
          rows={buses}
          keyField="bus_id"
          columns={[
            { key: "bus_id", header: "Smart Meter", className: "mono emphasis", render: (r) => `SM_${String(r.bus_id).padStart(2, "0")}` },
            { key: "consumer_type", header: "Type", render: (r) => <Badge tone="neutral">{r.consumer_type}</Badge> },
            { key: "voltage", header: "Voltage (pu)", className: "mono", render: (r) => r.voltage?.toFixed(4) },
            { key: "current", header: "Current (A)", className: "mono", render: (r) => r.current?.toFixed(2) },
            { key: "frequency", header: "Frequency (Hz)", className: "mono", render: (r) => r.frequency?.toFixed(3) },
            { key: "consumption", header: "Power (kW)", className: "mono", render: (r) => r.consumption?.toFixed(2) },
            {
              key: "attack_type", header: "Status",
              render: (r) => r.attack_type === "normal"
                ? <Badge tone="success">Normal</Badge>
                : <Badge tone="critical">{r.attack_type}</Badge>,
            },
          ]}
        />
      </Card>
    </div>
  );
}
