export function Badge({ tone = "neutral", children }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function StatusDot({ tone = "neutral" }) {
  return <span className={`status-dot ${tone}`} />;
}
