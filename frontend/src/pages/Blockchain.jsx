import { useState } from "react";
import { Blocks, ShieldCheck, ShieldAlert, Link2, Server, Wallet, ExternalLink, Database, UploadCloud, CheckCircle2 } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge, StatusDot } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { usePolling } from "../hooks/usePolling";
import {
  getBlockchainStatus, getOnchainStatus, getPinataStatus, getBlockchainBlocks,
  pinBlockToIpfs, verifyBlockOnIpfs,
} from "../api/client";

export default function Blockchain() {
  const local = usePolling(getBlockchainStatus, 8000);
  const onchain = usePolling(getOnchainStatus, 10000);
  const pinata = usePolling(getPinataStatus, 15000);
  const blocks = usePolling(() => getBlockchainBlocks(8), 8000);

  const localValid = !!local.data?.valid;
  const onchainEnabled = !!onchain.data?.enabled;
  const pinataEnabled = !!pinata.data?.enabled;

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

      <Card
        title="IPFS Storage (Pinata)"
        subtitle="Where each block's raw JSON actually lives — production/blockchain/pinata_bridge.py"
        style={{ marginBottom: "var(--space-4)" }}
      >
        {!pinataEnabled ? (
          <EmptyState
            icon={UploadCloud}
            title="IPFS pinning is not configured"
            description="Set PINATA_JWT on the backend to enable pinning block content to IPFS via Pinata."
          />
        ) : blocks.error || !blocks.data?.blocks?.length ? (
          <div className="empty-state"><div className="empty-state-title">No blocks to show yet</div></div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            <div className="type-small text-muted">
              Pinning is per-block and manual — a block isn't automatically uploaded to IPFS the moment it's
              sealed; click "Pin to IPFS" below to store that block's exact JSON there and get back a CID
              anyone can independently fetch and verify.
            </div>
            {blocks.data.blocks.map((block) => (
              <BlockRow key={block.index} block={block} />
            ))}
          </div>
        )}
      </Card>

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
          <br /><br />
          <strong>Note on IPFS/Pinata:</strong> the deployed <code>AnomalyRegistry</code> contract has no field for
          an IPFS CID — pinning a block's content to IPFS (above) and anchoring its hash on Ethereum (left) are two
          independent proofs today, not one linked pipeline. Verifying a pinned block re-fetches its exact JSON
          from a public IPFS gateway and recomputes its hash locally to confirm nothing was altered.
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

function BlockRow({ block }) {
  const [pinning, setPinning] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [pin, setPin] = useState(null);
  const [verification, setVerification] = useState(null);
  const [error, setError] = useState(null);

  async function handlePin() {
    setPinning(true);
    setError(null);
    try {
      const result = await pinBlockToIpfs(block.index);
      setPin(result);
      setVerification(null);
    } catch {
      setError("Pin failed — check PINATA_JWT is configured on the backend.");
    } finally {
      setPinning(false);
    }
  }

  async function handleVerify() {
    setVerifying(true);
    setError(null);
    try {
      const result = await verifyBlockOnIpfs(block.index);
      setVerification(result);
    } catch {
      setError("Verify failed — this block may not be pinned yet.");
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: 6, padding: "10px 12px",
      border: "1px solid var(--color-border)", borderRadius: 8,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Database size={13} className="text-muted" />
          <span className="type-small type-mono">Block #{block.index}</span>
          <span className="type-small text-muted">· {block.transaction_count} tx</span>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button className="topbar-icon-btn" style={{ width: "auto", padding: "4px 10px", fontSize: 12 }}
            onClick={handlePin} disabled={pinning}>
            {pinning ? "Pinning…" : pin ? "Re-pin" : "Pin to IPFS"}
          </button>
          {pin && (
            <button className="topbar-icon-btn" style={{ width: "auto", padding: "4px 10px", fontSize: 12 }}
              onClick={handleVerify} disabled={verifying}>
              {verifying ? "Verifying…" : "Verify integrity"}
            </button>
          )}
        </div>
      </div>
      <div className="type-small text-muted type-mono" style={{ wordBreak: "break-all" }}>
        hash: {block.block_hash?.slice(0, 24)}…
      </div>
      {pin && (
        <div className="type-small" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <UploadCloud size={12} className="text-muted" />
          <a href={pin.gateway_url} target="_blank" rel="noreferrer" style={{ color: "var(--color-primary)" }}>
            {pin.cid}
          </a>
          <ExternalLink size={11} className="text-muted" />
        </div>
      )}
      {verification && (
        <div className="type-small" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {verification.integrity_verified
            ? <><CheckCircle2 size={12} style={{ color: "var(--color-success)" }} /><span style={{ color: "var(--color-success)" }}>Integrity verified — recomputed hash matches</span></>
            : <><ShieldAlert size={12} style={{ color: "var(--color-critical)" }} /><span style={{ color: "var(--color-critical)" }}>Hash mismatch — content may have been altered</span></>}
        </div>
      )}
      {error && <div className="type-small" style={{ color: "var(--color-critical)" }}>{error}</div>}
    </div>
  );
}
