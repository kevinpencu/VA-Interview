export default function InvalidLink() {
  return (
    <div className="intro-shell" style={{ textAlign: "center" }}>
      <div className="eyebrow fade-in">Link unavailable</div>
      <h1 className="title-display fade-in-1" style={{ fontSize: "clamp(36px, 5vw, 56px)" }}>
        This link <em>isn't valid</em>.
      </h1>
      <p className="muted fade-in-2" style={{ marginTop: 24, fontSize: "var(--text-base)" }}>
        It may have already been used, or it never existed. If you were expecting access, contact the hiring manager who sent it.
      </p>
    </div>
  );
}
