"""devref_card, the display half of the Dev Reference bundle.

Server-side ``fetch()`` runs once per render: it resolves the cell's
selected ``board_id`` into the full board record by reading from
``devref_core``'s shared store, then returns a JSON-serialisable dict
the client paints from. This is the same pattern every "widget reads
shared state from a _core sibling" relationship uses.

The widget contract for server-side fetch:

  ``fetch(options, settings, ctx) -> Any``

  * ``options`` — the cell's options dict (i.e. what
    ``cell_options[*]`` in this plugin.json declared, populated with
    the user's choices).
  * ``settings`` — plugin-level settings (this plugin declares none;
    see ``devref_core`` for an example that uses them).
  * ``ctx`` — dict carrying ``panel_w``, ``panel_h``, ``preview``
    (True when rendered for the editor / previews, False on a real
    push), and ``data_dir`` (this plugin's data dir as a string).

  Returns anything JSON-serialisable. The composer hands it to the
  client as ``ctx.data`` in ``render(shadow, ctx)``. Returning
  ``{"error": "..."}`` is the convention for graceful failures so
  the client can render an error card instead of crashing.

Note we don't reach across to ``devref_core``'s module directly; we
go via the host's plugin registry. That makes the lookup symmetrical
to how an unrelated third-party plugin would have to do it, no
"sibling magic", and keeps the bundle's pieces loosely coupled.
"""

from __future__ import annotations

from typing import Any

from flask import current_app


def _resolve_board(board_id: str) -> dict[str, Any] | None:
    """Look up a board record by id from ``devref_core``'s store.

    Returns the board dict if found, ``None`` otherwise. Errors here
    are returned as None so the widget renders a "no board picked"
    state rather than crashing the cell."""
    if not board_id:
        return None
    registry = current_app.config.get("PLUGIN_REGISTRY")
    if registry is None:
        return None
    core = registry.get("devref_core")
    if core is None or core.server_module is None:
        return None
    list_boards = getattr(core.server_module, "list_boards", None)
    if list_boards is None:
        return None
    for board in list_boards():
        if board.get("id") == board_id:
            return board  # type: ignore[no-any-return]
    return None


def fetch(
    options: dict[str, Any],
    settings: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    """Resolve the cell's options into the data envelope the client
    paints from. Reading the board now (server-side) lets us return a
    self-contained snapshot, so the client never has to reach across
    plugin boundaries at render time."""
    board_id = str(options.get("board_id") or "")
    board = _resolve_board(board_id)
    if board is None and board_id:
        # User picked a board that no longer exists (deleted from the
        # admin page after the cell was configured). Surface a soft
        # error so the cell shows a recognisable empty state.
        return {
            "error": f"Board {board_id!r} not found, pick a current one in the cell editor.",
            "preview": bool(ctx.get("preview")),
        }
    return {
        "board": board,
        "preview": bool(ctx.get("preview")),
    }
