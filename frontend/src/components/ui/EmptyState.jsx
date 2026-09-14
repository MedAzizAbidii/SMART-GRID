export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="empty-state">
      {Icon && <div className="empty-state-icon"><Icon size={32} strokeWidth={1.5} /></div>}
      {title && <div className="empty-state-title">{title}</div>}
      {description && <div className="type-small">{description}</div>}
    </div>
  );
}

export function MockFlag() {
  return <span className="mock-flag">● Sample data — no live backend source</span>;
}
