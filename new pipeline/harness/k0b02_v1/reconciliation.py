from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical import require, sha256
from .publisher import _git, _known_commit
from .store import K0b02Store, runtime_profile


def reconcile(database: Path, repository: Path, publication_id: str) -> dict[str, Any]:
    connection = K0b02Store.connect(database)
    try:
        intent = connection.execute(
            "SELECT status,expected_git_parent FROM k0b02_publication_intents WHERE publication_id=?",
            (publication_id,),
        ).fetchone()
        require(intent is not None, "reconciliation:missing_intent")
        result = connection.execute(
            "SELECT git_commit,snapshot_sha256 FROM k0b02_publication_results WHERE publication_id=?",
            (publication_id,),
        ).fetchone()
        if result:
            return {
                "result": "terminal_original",
                "git_commit": result[0],
                "snapshot_sha256": result[1],
            }
        profile = runtime_profile(connection)
        commit = _known_commit(repository, publication_id)
        if not commit:
            require(
                _git(repository, "rev-parse", "HEAD") == intent[1],
                "reconciliation:ambiguous_unknown_effect",
            )
            return {"result": "safe_to_retry_no_effect"}
        checkpoint = repository / profile["checkpoint_path"]
        require(checkpoint.is_file(), "reconciliation:known_effect_missing_checkpoint")
        return {
            "result": "known_committed_effect",
            "git_commit": commit,
            "snapshot_sha256": sha256(checkpoint.read_bytes()),
        }
    finally:
        connection.close()
