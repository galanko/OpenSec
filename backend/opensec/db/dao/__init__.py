"""DAO modules for the EXEC-0002 tables (assessment, posture_check, completion).

Keeps the new-tables CRUD separate from the legacy ``repo_*`` modules so Session B's
owns list is unambiguous. Style mirrors ``repo_finding.py``: module-level async
functions taking an ``aiosqlite.Connection``, ``_row_to_*`` helpers, JSON-encoded
columns serialized with ``json.dumps``/``json.loads``, UUID ids, UTC ISO timestamps.
"""
