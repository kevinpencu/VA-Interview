export default function SubmitScreen() {
  return (
    <div className="intro-shell" style={{ textAlign: "center" }}>
      <div className="eyebrow fade-in">Test complete</div>
      <h1 className="title-display fade-in-1">
        <em>Thank you.</em>
      </h1>
      <p className="fade-in-2" style={{ marginTop: 28, fontSize: "var(--text-lg)", color: "var(--color-text-soft)" }}>
        We've received your answers. The team will review them and be in touch.
      </p>
      <p className="fade-in-3 muted" style={{ marginTop: 16, fontSize: "var(--text-sm)" }}>
        You can close this tab now.
      </p>
    </div>
  );
}
