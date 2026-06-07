// devref_card, the display half of the Dev Reference bundle.
//
// Renders the picked board's data into the cell, with every
// cell_option type from the manifest wired through:
//
//   board_id          (select with choices_from)  → resolved by
//                                                    server.py:fetch
//                                                    into ctx.data.board
//   title_override    (string)                    → swaps board.name
//   subtitle          (textarea)                  → body paragraph
//   stat_value        (number)                    → headline stat
//   stat_label        (string)                    → caption under stat
//   variant           (select)                    → layout style
//   show_sections     (multiselect)               → which blocks paint
//   use_accent_bg     (boolean)                   → tinted surface
//   accent_override   (color)                     → swaps board.accent
//
// The whole render is pure inline DOM + CSS, no network, no setInterval.
// E-ink dashboards refresh on push (typically every few minutes), so a
// static read on each render is enough; if your widget needs higher
// frequency, prefer a server.py poll cached via the data envelope.
//
// Sizes (xs/sm/md/lg) come from ctx.cell.size. CSS handles fluid
// scaling; we only branch on size for "should we show the body at
// xs?" kind of decisions.

export default function render(shadow, ctx) {
  const data = ctx?.data ?? {};
  const opts = ctx?.cell?.options ?? {};
  const size = ctx?.cell?.size ?? "md";

  // ----- error / empty states -------------------------------------
  if (data.error) {
    shadow.innerHTML = `
      ${baseStyles()}
      <div class="card error">
        <div class="head"><i class="ph-bold ph-warning-circle"></i><span>devref_card</span></div>
        <p class="body">${escapeHtml(data.error)}</p>
      </div>`;
    return;
  }

  const board = data.board || null;
  if (!board) {
    shadow.innerHTML = `
      ${baseStyles()}
      <div class="card empty">
        <div class="head"><i class="ph-bold ph-blueprint"></i><span>devref_card</span></div>
        <p class="body">Pick a board in the cell editor to populate this card. Save boards in <code>Settings → Plugins → Dev Reference, Core</code>.</p>
      </div>`;
    return;
  }

  // ----- resolve options into render values -----------------------
  const title = (opts.title_override || board.name || "Untitled").toString();
  const subtitle = (opts.subtitle || "").toString();
  const statValue = numberOr(opts.stat_value, 42);
  const statLabel = (opts.stat_label || "items").toString();
  const variant = ["balanced", "stat_hero", "body_first"].includes(opts.variant)
    ? opts.variant
    : "balanced";
  const showSet = new Set(
    Array.isArray(opts.show_sections) && opts.show_sections.length
      ? opts.show_sections
      : ["title", "body", "stat", "footer"],
  );
  const useAccentBg = opts.use_accent_bg !== false;
  const accent = (opts.accent_override || board.accent || "#0ea5e9").toString();

  // ----- compose layout based on variant + size -------------------
  const bodyText = subtitle || board.body || "";
  // At xs we drop the body to save vertical space; the title + stat
  // are higher-information density.
  const showBody = showSet.has("body") && bodyText && size !== "xs";

  const titleBlock = showSet.has("title")
    ? `<header class="title-block">
         <h1>${escapeHtml(title)}</h1>
       </header>`
    : "";

  const bodyBlock = showBody
    ? `<p class="body">${escapeHtml(bodyText)}</p>`
    : "";

  const statBlock = showSet.has("stat")
    ? `<div class="stat">
         <span class="stat-value">${escapeHtml(formatStat(statValue))}</span>
         <span class="stat-label">${escapeHtml(statLabel)}</span>
       </div>`
    : "";

  const footerBlock = showSet.has("footer")
    ? `<footer class="footer">
         <code>${escapeHtml(board.id)}</code>
         <span class="dot" aria-hidden="true"></span>
         <span>devref_card</span>
       </footer>`
    : "";

  // Variant decides the visual ordering. CSS Grid handles the actual
  // box sizing; we just reorder children.
  const order = {
    balanced: [titleBlock, bodyBlock, statBlock, footerBlock],
    stat_hero: [statBlock, titleBlock, bodyBlock, footerBlock],
    body_first: [bodyBlock, titleBlock, statBlock, footerBlock],
  }[variant];

  shadow.innerHTML = `
    ${baseStyles()}
    <div class="card variant-${variant} size-${size}${useAccentBg ? " accent-bg" : ""}"
         style="--accent: ${escapeAttr(accent)};">
      ${order.join("")}
    </div>`;
}

// ----- helpers ------------------------------------------------------

function numberOr(value, fallback) {
  const n = Number.parseFloat(value);
  return Number.isFinite(n) ? n : fallback;
}

function formatStat(n) {
  // Compact representation for big numbers so a "stat hero" layout
  // doesn't overflow the cell at small sizes.
  if (Math.abs(n) >= 10000) {
    return new Intl.NumberFormat(undefined, {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(n);
  }
  return String(Number.isInteger(n) ? n : n.toFixed(1));
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}

function escapeAttr(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}

function baseStyles() {
  // All styles inline so the widget renders standalone (no external
  // CSS link the renderer has to wait on). Variables from the host
  // composer (--surface, --fg, --muted, --font, ...) are used where
  // available; we fall back to sane defaults otherwise so the widget
  // looks reasonable in any theme.
  return `<style>
    :host { display: block; height: 100%; width: 100%; }
    * { box-sizing: border-box; }
    .card {
      position: relative;
      height: 100%;
      width: 100%;
      padding: clamp(0.8rem, 3vw, 1.6rem);
      display: grid;
      grid-template-rows: auto 1fr auto auto;
      gap: clamp(0.4rem, 1.2vw, 0.8rem);
      background: var(--surface, #fff);
      color: var(--fg, #111);
      font-family: var(--font, system-ui, -apple-system, sans-serif);
      overflow: hidden;
    }
    .card.accent-bg {
      background:
        linear-gradient(135deg,
          color-mix(in oklab, var(--accent) 14%, var(--surface, #fff)) 0%,
          var(--surface, #fff) 70%);
    }
    .card::before {
      content: "";
      position: absolute;
      inset: 0 auto 0 0;
      width: 4px;
      background: var(--accent);
    }
    .title-block h1 {
      margin: 0;
      font-size: clamp(1rem, 3.6vw, 2rem);
      font-weight: 700;
      line-height: 1.15;
      letter-spacing: -0.01em;
      color: var(--accent);
    }
    .body {
      margin: 0;
      font-size: clamp(0.78rem, 1.8vw, 1.05rem);
      line-height: 1.5;
      color: var(--fg-soft, var(--fg, #333));
      white-space: pre-wrap;
      overflow-wrap: break-word;
    }
    .stat {
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
      padding: 0.4rem 0;
      border-top: 1px solid color-mix(in oklab, var(--fg, #000) 12%, transparent);
      border-bottom: 1px solid color-mix(in oklab, var(--fg, #000) 12%, transparent);
    }
    .stat-value {
      font-size: clamp(1.4rem, 6vw, 3rem);
      font-weight: 800;
      font-variant-numeric: tabular-nums;
      letter-spacing: -0.03em;
      line-height: 1;
    }
    .stat-label {
      font-size: clamp(0.75rem, 1.4vw, 0.95rem);
      color: var(--muted, var(--fg-soft, #666));
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .footer {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.75rem;
      color: var(--muted, #888);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .footer code {
      background: color-mix(in oklab, var(--fg, #000) 8%, transparent);
      padding: 0.05rem 0.4rem;
      border-radius: 3px;
      font-size: 0.7rem;
      letter-spacing: 0;
      text-transform: none;
    }
    .footer .dot {
      width: 4px; height: 4px; border-radius: 50%;
      background: var(--muted, #888);
    }
    .card.variant-stat_hero .stat {
      border-top: none;
      border-bottom: 2px solid var(--accent);
      padding-top: 0;
    }
    .card.variant-stat_hero .stat-value {
      font-size: clamp(2rem, 9vw, 5rem);
      color: var(--accent);
    }
    .card.size-xs { padding: 0.6rem 0.8rem; gap: 0.3rem; }
    .card.size-xs .stat-value { font-size: clamp(1.2rem, 5vw, 1.8rem); }
    .card.size-xs .footer { display: none; }
    .card.error .body { color: var(--danger, #c0392b); }
    .card.empty .body { color: var(--muted, #999); }
    .head {
      display: flex; align-items: center; gap: 0.4rem;
      font-size: 0.85rem; color: var(--muted, #888);
      text-transform: uppercase; letter-spacing: 0.06em;
    }
  </style>`;
}
