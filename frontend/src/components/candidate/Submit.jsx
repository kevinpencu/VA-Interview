export default function SubmitScreen() {
  return (
    <div className="intro-shell" style={{ textAlign: "center" }}>
      <div className="eyebrow fade-in">Test complete</div>
      <h1 className="intro-title fade-in-1">Thank you.</h1>
      <p className="fade-in-2" style={{ marginTop: 20, fontSize: "var(--text-lg)", color: "var(--text-soft)" }}>
        We've received your answers. The team will review them and be in touch.
      </p>
      <p className="fade-in-3 muted" style={{ marginTop: 14, fontSize: "var(--text-sm)" }}>
        You can close this tab.
      </p>
    </div>
  );
}
