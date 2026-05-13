export default function InvalidLink() {
  return (
    <div className="intro-shell" style={{ textAlign: "center" }}>
      <div className="eyebrow fade-in">Link unavailable</div>
      <h1 className="intro-title fade-in-1" style={{ fontSize: "clamp(32px, 4vw, 48px)" }}>
        This link isn't valid.
      </h1>
      <p className="muted fade-in-2" style={{ marginTop: 16, fontSize: "var(--text-base)" }}>
        It may have already been used, or it never existed. Contact the hiring manager who sent it.
      </p>
    </div>
  );
}
