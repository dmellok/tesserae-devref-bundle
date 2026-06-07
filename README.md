# Dev Reference Bundle (Tesserae)

A worked example for [Tesserae](https://github.com/dmellok/tesserae)
widget developers. Pairs an admin-only `_core` plugin with a display
widget that exercises every contract surface:

- `cell_options` of every type — `string`, `textarea`, `number`,
  `select`, `multiselect`, `boolean`, `color`, and a `select` with
  `choices_from` (dynamic options sourced from another plugin's
  `choices()`).
- A `server.py` with `fetch()` returning the data envelope the client
  paints from.
- A `server.py` with `blueprint()` mounting a `/plugins/devref_core/`
  admin page.
- A shared-state pattern (`_core` owns data, display widget reads it).
- A `multiselect` driving which UI sections render.
- Theme-token-aware CSS that scales fluidly across `xs/sm/md/lg`.
- A `boolean` toggling a visual treatment, a `color` overriding a
  shared-state default.

Install both folders together via the Tesserae widget marketplace
(Settings → Plugins → Browse community widgets → "Dev Reference"); the
bundle install drops `devref_core/` and `devref_card/` as siblings
under `plugins/`.

## Layout (the tarball that ships to the catalog)

```
devref-bundle-v0.1.0/        ← single wrapping folder (any name; the
                                marketplace strips it)
  devref_core/                ← admin-only data plugin
    plugin.json               ← manifest (kind: "data")
    server.py                 ← blueprint() + choices() + storage
    templates/
      devref_core/
        index.html            ← admin page
  devref_card/                ← display widget
    plugin.json               ← manifest (kind: "widget")
    server.py                 ← fetch()
    client.js                 ← render()
```

## What's where

### `devref_core/`

**`plugin.json`** — `kind: "data"`, no widget render. Declares
plugin-level `settings` (the host renders these under Settings →
Plugins → Dev Reference, Core); leave the `cell_options` array out
because a `data` plugin doesn't sit in cells.

**`server.py`** — exports three functions:

- `blueprint() -> Blueprint`: a Flask blueprint mounted at
  `/plugins/devref_core/`. Routes for create / delete; uses the
  standard `card_head` macros for visual consistency.
- `choices(name: str) -> list[{value, label}]`: powers the
  `devref_card`'s `board_id` dropdown. The widget's manifest sets
  `choices_from: "boards"`, and the host calls back into this
  function with `name="boards"`.
- `list_boards() -> list[dict]`: a small read API the widget's
  `fetch()` reads through. Not required by the contract — anything
  exported from `server.py` is callable from a sibling plugin via the
  host's plugin registry — but it makes the contract between the two
  folders explicit.

**`templates/devref_core/index.html`** — Jinja2 admin page extending
`_base.html`. Lives under `templates/<plugin_id>/` because Flask
namespaces blueprint templates by folder; the `index.html` directly
inside `templates/` would collide with the host's homepage template.

### `devref_card/`

**`plugin.json`** — `kind: "widget"`. Declares `cell_options` with
every supported type:

```jsonc
{
  // dynamic, sourced from devref_core.choices("boards")
  "name": "board_id",
  "type": "select",
  "choices_from": "boards"
},
{
  "name": "title_override",
  "type": "string"        // one-line text input
},
{
  "name": "subtitle",
  "type": "textarea"      // multi-line text input
},
{
  "name": "stat_value",
  "type": "number",
  "min": 0, "max": 9999   // numeric with constraints
},
{
  "name": "variant",
  "type": "select",       // static options inline
  "choices": [ ... ]
},
{
  "name": "show_sections",
  "type": "multiselect",  // multi-pick with defaults
  "default": ["title", "body", "stat", "footer"],
  "choices": [ ... ]
},
{
  "name": "use_accent_bg",
  "type": "boolean"       // switch / checkbox
},
{
  "name": "accent_override",
  "type": "color"         // colour picker
}
```

`render.dither: "none"` and `render.needs_network: false` round it
out. The `dither` field is a hint to the e-ink renderers; `none` is
right for content that's already palette-aware.

**`server.py`** — exports `fetch(options, settings, ctx)`. The host
calls this once per render and passes the result as `ctx.data` to
the client. Returns either `{board, preview}` (happy path) or
`{error, preview}` (soft failure, e.g. the picked board was deleted
after the cell was configured). The board is looked up via the host's
plugin registry, the symmetrical way every third-party widget would
reach into `devref_core`.

**`client.js`** — exports `default function render(shadow, ctx)`.
Reads `ctx.data` (from `fetch()`) and `ctx.cell.options` (from the
cell's saved configuration), resolves them into a render envelope,
and writes inline HTML + CSS into the shadow root. Pure inline DOM:
no network at render time, no setInterval (e-ink dashboards refresh
on push, not on a ticking clock).

## Contract gotchas

1. **The widget's `render(shadow, ctx)` runs in a shadow DOM.** CSS
   inside the shadow can't be reached by host page styles, and vice
   versa. Inline `<style>` blocks inside the shadow are the standard
   pattern; the host's theme tokens (`--surface`, `--fg`,
   `--accent-1`, etc.) DO pierce into the shadow (they're CSS
   variables declared on the host element), so the widget can opt
   into the active dashboard theme.
2. **Cross-plugin reads go through the registry.** Use
   `current_app.config["PLUGIN_REGISTRY"].get("other_plugin")` then
   `getattr(plugin.server_module, "fn", None)`. Direct imports
   (`from devref_core import ...`) work in development but break
   when the bundle is installed under unfamiliar paths.
3. **Cell options resolve at render time.** The host serializes the
   user's cell options into the cell record and re-injects them on
   every push. Don't store render-time state in `server.py` module
   globals — render N times across N devices and you'll see surprising
   crosstalk. Use the plugin's `data_dir` for persisted state.
4. **`fetch()` should always return a dict.** Returning `None` is
   treated as "no data", which the client has to special-case.
   Returning `{"error": "..."}` is the convention for soft failures
   so the cell renders an error card instead of crashing.
5. **`choices_from` resolves on the SAME plugin only.** The host
   calls `<this_plugin>.server_module.choices(name)` when populating
   a cell-option dropdown; it does NOT walk the registry looking for
   a sibling's `choices()`. So a widget that wants to pull options
   from a `_core` sibling must expose its own `choices()` that
   delegates. See `devref_card/server.py` for the one-line
   delegation pattern: `devref_card.choices("boards")` calls
   `devref_core.choices("boards")` through the registry.

## License

MIT.
