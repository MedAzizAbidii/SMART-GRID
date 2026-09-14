import { Blocks, ShieldCheck, ShieldAlert, Link2, Server, Wallet, ExternalLink } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge, StatusDot } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { usePolling } from "../hooks/usePolling";
import { getBlockchainStatus, getOnchainStatus } from "../api/client";

export default function Blockchain() {
  const local = usePolling(getBlockchainStatus, 8000);
  const onchain = usePolling(getOnchainStatus, 10000);

  const localValid = !!local.data?.valid;
  const onchainEnabled = !!onchain.data?.enabled;

  return (
    <div>
      <div className="page-header">
        <div className="page-header-title">
          <h1 className="type-h2">Blockchain — Trust Layer</h1>
          <Badge tone={local.error ? "critical" : localValid ? "success" : "warning"}>
            <StatusDot tone={local.error ? "critical" : localValid ? "success" : "warning"} />
            {local.error ? "Offline" : localValid ? "Chain valid" : "Validation issues"}
          </Badge>
        </div>
        <p className="text-secondary type-small" style={{ marginTop: 4 }}>
          Two layers: a local Proof-of-Authority ledger notarizes every detected anomaly in real time, and an
          optional real Ethereum anchor (Sepolia) gives it public, tamper-evident timestamping.
        </p>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: "var(--space-4)", alignItems: "start" }}>
        {/* Local PoA ledger */}
        <Card title="Local PoA Ledger" subtitle="blockchain/poa_ledger.py · Ed25519-signed">
          {local.error ? (
            <EmptyState icon={ShieldAlert} title="Ledger unavailable" description="check api_server.py is running" />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
              <StatRow icon={Blocks} label="Total blocks" value={local.data?.blocks ?? "—"} />
              <StatRow
                icon={localValid ? ShieldCheck : ShieldAlert}
                label="Integrity"
                value={localValid ? "All signatures & hashes verified" : `${local.data?.errors?.length ?? 0} error(s)`}
                badge={localValid ? "success" : "critical"}
              />
              <div>
                <div className="type-small text-muted" style={{ marginBottom: 8 }}>Authority nodes (Ed25519)</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {(local.data?.authorities || []).map((label) => (
                    <Badge key={label} tone="info">{label}</Badge>
                  ))}
                </div>
              </div>
              {!localValid && local.data?.errors?.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {local.data.errors.slice(0, 5).map((err, i) => (
                    <div key={i} className="type-small" style={{ color: "var(--color-critical)" }}>{err}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>

        {/* Real on-chain anchor */}
        <Card title="On-Chain Anchor" subtitle="onchain/contracts · Solidity · Sepolia testnet">
          {onchain.error ? (
            <EmptyState icon={ShieldAlert} title="Could not reach backend" description="check api_server.py is running" />
          ) : !onchainEnabled ? (
            <EmptyState
              icon={Link2}
              title="On-chain anchoring is disabled"
              description={
                onchain.data?.reason ||
                "Off by default. Set SGRID_ONCHAIN_ENABLED=1, SGRID_ONCHAIN_RPC_URL and SGRID_ONCHAIN_PRIVATE_KEY on the backend to publish PoA block hashes to a real Ethereum network."
              }
            />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
              <StatRow icon={Server} label="Network" value={onchain.data.network} badge="success" />
              <StatRow icon={Wallet} label="Operator account" value={shortAddr(onchain.data.account)} />
              <StatRow icon={Wallet} label="Balance" value={`${onchain.data.balance_eth?.toFixed(4)} ETH`} />
              <StatRow icon={Blocks} label="PoA blocks anchored" value={onchain.data.anchor_count} />
              <StatRow icon={ShieldCheck} label="Anomalies recorded on-chain" value={onchain.data.anomaly_record_count} />
              <div>
                <div className="type-small text-muted" style={{ marginBottom: 8 }}>Deployed contracts</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {Object.entries(onchain.data.contracts || {}).map(([name, address]) => (
                    <div key={name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span className="type-small text-muted">{name}</span>
                      <a
                        className="type-small type-mono"
                        style={{ color: "var(--color-primary)", display: "flex", alignItems: "center", gap: 4 }}
                        href={`https://sepolia.etherscan.io/address/${address}`}
                        target="_blank" rel="noreferrer"
                      >
                        {shortAddr(address)} <ExternalLink size={11} />
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>

      <Card title="How the two layers connect">
        <div className="type-small text-secondary" style={{ lineHeight: 1.7 }}>
          Every AI-detected anomaly is first notarized in the local PoA ledger (SHA-256 block hash, signed by an
          Ed25519 authority key). When on-chain anchoring is enabled, the backend periodically calls{" "}
          <code>PoAAnchor.anchorBlock()</code> to publish that block's hash on Ethereum — giving anyone a way to
          verify a detection existed at or before a given time, without paying gas to store full grid telemetry
          on-chain. High-confidence anomalies are additionally recorded individually via{" "}
          <code>AnomalyRegistry.recordAnomaly()</code>, each carrying the off-chain block hash that links the two
          layers together. Only addresses registered in <code>AuthorityRegistry</code> may write to either
          contract.
        </div>
      </Card>
    </div>
  );
}

function StatRow({ icon: Icon, label, value, badge }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <span className="type-small text-muted" style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {Icon && <Icon size={14} />} {label}
      </span>
      {badge ? <Badge tone={badge}>{value}</Badge> : <span className="type-small type-mono" style={{ fontWeight: 600 }}>{value}</span>}
    </div>
  );
}

function shortAddr(address) {
  if (!address) return "—";
  return `${address.slice(0, 6)}…${address.slice(-4)}`;
}
