from __future__ import annotations

import os
import tempfile
from pathlib import Path


def configure_temp_environment() -> tuple[Path, Path]:
    root = Path(tempfile.mkdtemp(prefix="forgevault-ci-"))
    source = root / "source"
    vault = root / "vault"
    staging = root / "staging"
    outbox = root / "jobboss2" / "outbox"
    source.mkdir(parents=True, exist_ok=True)
    vault.mkdir(parents=True, exist_ok=True)
    staging.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)

    os.environ["FORGEVAULT_DATABASE_URL"] = f"sqlite+pysqlite:///{(root / 'forgevault.db').as_posix()}"
    os.environ["FORGEVAULT_LOCAL_VAULT_ROOT"] = str(vault)
    os.environ["FORGEVAULT_STAGING_ROOT"] = str(staging)
    os.environ["FORGEVAULT_JOBBOSS2_OUTBOX_ROOT"] = str(outbox)
    os.environ["FORGEVAULT_AUTO_CREATE_SCHEMA"] = "true"
    os.environ["FORGEVAULT_ENABLE_DESKTOP_BRIDGE"] = "true"
    return root, source


def assert_status(response, expected: int = 200):
    if response.status_code != expected:
        raise AssertionError(f"Expected HTTP {expected}, got {response.status_code}: {response.text}")
    return response.json()


def main() -> None:
    root, source = configure_temp_environment()
    (source / "12345_A_demo_print.txt").write_text("ForgeVault CI demo file\n", encoding="utf-8")
    (source / "assy_demo.SLDASM").write_text("placeholder assembly\n", encoding="utf-8")
    (source / "readme.tmp").write_text("ignored temporary file\n", encoding="utf-8")

    from fastapi.testclient import TestClient

    from forgevault.desktop import configure_desktop_environment, default_home
    from forgevault.main import app

    assert default_home().name == "ForgeVault"
    configure_desktop_environment(root / "desktop-home")

    with TestClient(app) as client:
        assert_status(client.get("/healthz"))
        ui = client.get("/ui")
        if ui.status_code != 200 or "ForgeVault Desktop" not in ui.text:
            raise AssertionError(f"UI smoke failed: {ui.status_code}")

        caps = assert_status(client.get("/api/v1/desktop/capabilities"))
        if not caps.get("desktop_bridge_enabled"):
            raise AssertionError(f"desktop bridge should be enabled in CI smoke: {caps}")

        status = assert_status(client.get("/api/v1/setup/status"))
        if not status["needs_source_folder"]:
            raise AssertionError(f"fresh setup should need a source folder: {status}")

        folder = assert_status(
            client.post(
                "/api/v1/source-folders",
                json={"path": str(source), "display_name": "CI Source", "actor": "ci", "recursive": True, "include_hidden": False},
            ),
            201,
        )
        if folder["display_name"] != "CI Source":
            raise AssertionError(folder)

        folders = assert_status(client.get("/api/v1/source-folders"))
        if len(folders) != 1:
            raise AssertionError(f"expected one source folder, got {folders}")

        indexed = assert_status(client.post(f"/api/v1/source-folders/{folder['id']}/index", json={"actor": "ci", "max_files": 50}))
        if indexed["scanned"] != 2 or indexed["ingested"] != 2 or indexed["failed"] != 0:
            raise AssertionError(f"unexpected index result: {indexed}")

        results = assert_status(client.get("/api/v1/search", params={"q": "UNMAPPED"}))
        if not results:
            raise AssertionError("search did not return indexed unmapped record")
        record_id = results[0]["record"]["internal_record_id"]
        file_type = results[0]["latest_version"]["version_metadata"].get("file_type", {})
        if "category" not in file_type:
            raise AssertionError(f"file type metadata missing: {results[0]}")

        checkout = assert_status(client.post(f"/api/v1/records/{record_id}/checkout", json={"actor": "ci", "reason": "smoke"}), 201)
        if checkout["checked_out_by"] != "ci":
            raise AssertionError(checkout)

        checkout_status = assert_status(client.get(f"/api/v1/records/{record_id}/checkout"))
        if not checkout_status["is_checked_out"]:
            raise AssertionError(checkout_status)

        review = assert_status(
            client.post(
                "/api/v1/reviews",
                json={
                    "request_type": "pending_checkin",
                    "submitted_by": "ci",
                    "assigned_checker": "checker@example.com",
                    "entity_type": "records",
                    "entity_id": record_id,
                    "summary": "CI review request",
                    "reason": "Exercise review queue behavior",
                    "risk_level": "medium",
                    "details": {"source": "ci_smoke"},
                },
            ),
            201,
        )
        if review["status"] != "pending":
            raise AssertionError(review)

        pending = assert_status(client.get("/api/v1/reviews", params={"status_filter": "pending"}))
        if not pending:
            raise AssertionError("review queue did not return pending review")

        decided = assert_status(client.post(f"/api/v1/reviews/{review['id']}/decision", json={"reviewer": "checker", "decision": "approved", "comment": "CI approved"}))
        if decided["status"] != "approved":
            raise AssertionError(decided)

        notifications = assert_status(client.get("/api/v1/notifications"))
        if len(notifications) < 2:
            raise AssertionError(f"expected review requested/approved notifications, got {notifications}")

        assert_status(client.delete(f"/api/v1/records/{record_id}/checkout", json={"actor": "ci", "reason": "smoke cleanup", "force": False}))

        removed = assert_status(
            client.delete(
                f"/api/v1/source-folders/{folder['id']}",
                json={"actor": "ci", "confirm_remove_from_index_only": True},
            )
        )
        if removed["is_active"]:
            raise AssertionError(removed)

    print("ForgeVault CI smoke OK")


if __name__ == "__main__":
    main()
