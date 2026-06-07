"""devref_core, admin-only data plugin for the dev-reference bundle.

Pairs with the ``devref_card`` widget to demonstrate the shared-state
pattern: a ``_core`` plugin owns the data (here, a list of named
"boards"), and one or more display widgets pick from that list via
``choices_from``. Mirrors how ``glances_core`` + ``glances_status``
or ``picture_gallery`` work, kept deliberately small so the patterns
read cleanly end-to-end.

The shape on disk lives at ``data/plugins/devref_core/boards.json``::

    {
      "boards": [
        {
          "id":          "morning-routine",   # slug, stable across renames
          "name":        "Morning routine",   # display label
          "accent":      "#0ea5e9",           # hex colour
          "body":        "Coffee, stretch, …",# free-form text
          "created_at":  "ISO timestamp"
        },
        ...
      ]
    }

Three contract pieces a `_core` / data plugin exports:

  * ``blueprint()`` — Flask Blueprint mounted at
    ``/plugins/devref_core/`` (the host wires it in via
    plugin_loader.register_routes).
  * ``choices(name)`` — populates widget cell-option dropdowns that
    set ``choices_from: "<name>"``. Returns a list of
    ``{"value": id, "label": display}`` dicts.
  * ``list_boards()`` — a small read API the widget's server.py
    calls inside its ``fetch()`` to resolve a board id into its
    full record. Not required by the contract, just convenient.

mypy --strict is not enforced on community widgets; this file uses
type hints anyway because they help future readers.
"""

from __future__ import annotations

import json
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.wrappers import Response

# ----- storage helpers ------------------------------------------------
#
# Pattern: a single ``boards.json`` file inside the plugin's data_dir.
# Read-modify-write is fine for the single-user admin case Tesserae
# targets; switch to sqlite if your plugin ever wants concurrent
# writers (e.g. a background poller + the admin UI).


def _data_dir() -> Path:
    """Resolve the plugin's data_dir from the host's plugin registry.

    Tesserae creates ``data/plugins/<plugin_id>/`` on first start and
    hands the path to each plugin via the registry. Reading it here
    (rather than hard-coding the path) means the plugin works under
    any TESSERAE_DATA_DIR override, including pytest's tmp_path."""
    registry = current_app.config["PLUGIN_REGISTRY"]
    plugin = registry.get("devref_core")
    if plugin is None:
        raise RuntimeError("devref_core plugin not registered")
    return plugin.data_dir  # type: ignore[no-any-return]


def _store_path(data_dir: Path | None = None) -> Path:
    return (data_dir or _data_dir()) / "boards.json"


def _load(data_dir: Path | None = None) -> dict[str, Any]:
    """Read the boards file. Missing / corrupt file = empty list, so a
    fresh install (or a borked write) doesn't blow up the admin page."""
    path = _store_path(data_dir)
    if not path.exists():
        return {"boards": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"boards": []}
    if not isinstance(data, dict) or not isinstance(data.get("boards"), list):
        return {"boards": []}
    return data


def _save(data: dict[str, Any], data_dir: Path | None = None) -> None:
    """Atomic-ish write: tmp file + rename. The rename is atomic on the
    same filesystem, so a crash mid-write can't truncate the live file."""
    path = _store_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    """Turn a display name into a URL-safe stable id. Falls back to a
    random suffix when the name is non-ASCII or empty, so the resulting
    id is always usable as a filesystem / URL fragment."""
    base = _SLUG_RE.sub("-", name.lower()).strip("-")
    if not base:
        base = "board"
    return f"{base}-{secrets.token_hex(2)}"


# ----- public read API ------------------------------------------------
#
# These two functions are what the rest of the bundle (and any
# third-party widget) reads to resolve a board id into its data. Keep
# the shape stable, the widget's render path is the consumer.


def list_boards() -> list[dict[str, Any]]:
    """Snapshot of every saved board. Consumed by ``devref_card``'s
    ``fetch()`` to resolve the cell's picked id into the board's
    full record."""
    return list(_load().get("boards", []))


def choices(name: str) -> list[dict[str, str]]:
    """Powers any cell_option whose manifest sets
    ``choices_from: "boards"``. The host calls this when rendering
    the cell-edit panel, the dropdown's options are whatever this
    returns. ``name`` is the key the manifest passed; respect it so a
    plugin can expose multiple distinct choice lists if needed."""
    if name != "boards":
        return []
    return [{"value": b["id"], "label": b.get("name") or b["id"]} for b in list_boards()]


# ----- admin blueprint ------------------------------------------------
#
# A plugin gets a ``/plugins/<id>/`` admin route when its server.py
# exports a ``blueprint()`` factory. The Plugins nav dropdown lists
# the plugin under "Admin pages", and the Settings UI links to it
# from the per-plugin settings card.


def blueprint() -> Blueprint:
    bp = Blueprint("devref_core_admin", __name__, template_folder="templates")

    @bp.get("/")
    def index() -> str:
        data = _load()
        return render_template(
            "devref_core/index.html",
            boards=data.get("boards", []),
        )

    @bp.post("/boards")
    def create() -> Response:
        name = (request.form.get("name") or "").strip()
        accent = (request.form.get("accent") or "#0ea5e9").strip()
        body = (request.form.get("body") or "").strip()
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("devref_core_admin.index"))
        data = _load()
        boards = data.setdefault("boards", [])
        boards.append(
            {
                "id": _slugify(name),
                "name": name,
                "accent": accent,
                "body": body,
                "created_at": _now_iso(),
            }
        )
        _save(data)
        flash(f"Added board {name!r}.", "ok")
        return redirect(url_for("devref_core_admin.index"))

    @bp.post("/boards/<board_id>/delete")
    def delete(board_id: str) -> Response:
        data = _load()
        boards = data.get("boards", [])
        before = len(boards)
        data["boards"] = [b for b in boards if b.get("id") != board_id]
        if len(data["boards"]) == before:
            abort(404)
        _save(data)
        flash(f"Deleted board {board_id!r}.", "ok")
        return redirect(url_for("devref_core_admin.index"))

    return bp
