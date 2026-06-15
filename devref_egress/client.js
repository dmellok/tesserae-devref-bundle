// devref_egress, network-egress contract demo. Renders the fetched
// payload (or the error from a denied host) plus a footer that shows
// the requires line the manifest declares, so the cell itself
// communicates "this is what the contract looks like in source".

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

const REQUIRES_LINE = '"requires": ["network:api.github.com"]';

export default function render(shadow, ctx) {
  const data = ctx?.data ?? {};
  const css = `<link rel="stylesheet" href="/static/style/spectra-widgets.css">`;
  const scenario = data.scenario || "allowed";
  const url = data.url || "";
  const ok = !data.error;
  const heroColor = ok ? "var(--accent-3)" : "var(--accent-1)";
  const headline = ok ? "ALLOWED" : "BLOCKED";
  const glyph = ok ? "ph-shield-check" : "ph-shield-warning";

  const payloadBlock = (() => {
    if (!ok) {
      return `<p class="u-muted" style="margin:0;font-variant-numeric:tabular-nums">${escapeHtml(data.error)}</p>`;
    }
    const p = data.payload;
    if (typeof p === "string") {
      return `<blockquote class="u-quote" style="margin:0;font-style:italic">${escapeHtml(p)}</blockquote>`;
    }
    return `<pre style="margin:0;font-size:var(--fs-caption);white-space:pre-wrap;overflow:hidden">${escapeHtml(JSON.stringify(p, null, 2))}</pre>`;
  })();

  shadow.innerHTML = `
    ${css}
    <div class="w" data-widget="devref_egress">
      <div class="w-title">
        <i class="ph-bold ${glyph}" style="color:${heroColor}"></i>
        <h3>Egress demo</h3>
        <span class="pill" style="background:${heroColor};color:var(--on-accent)">${escapeHtml(headline)}</span>
      </div>
      <div class="w-body" style="display:flex;flex-direction:column;gap:var(--space-2)">
        <div style="display:flex;flex-direction:column;gap:var(--space-1)">
          <span class="u-label">Fetched</span>
          <code style="font-size:var(--fs-caption);word-break:break-all;color:var(--text-secondary)">${escapeHtml(url)}</code>
        </div>
        ${payloadBlock}
        <div style="display:flex;flex-direction:column;gap:var(--space-1);margin-top:auto">
          <span class="u-label">Declared in plugin.json</span>
          <code style="font-size:var(--fs-caption);background:var(--surface-sunken);padding:var(--space-1) var(--space-2);border-radius:var(--radius-1);color:var(--text-primary)">${escapeHtml(REQUIRES_LINE)}</code>
        </div>
      </div>
    </div>`;
}
