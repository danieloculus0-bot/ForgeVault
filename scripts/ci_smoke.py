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
        if "openForgeVaultCheckinFlow" not in ui.text or "Check In New Version" not in ui.text:
            raise AssertionError("UI check-in script was not injected into /ui")
        if "Start here" not in ui.text or "Choose Folder Now" not in ui.text:
            raise AssertionError("UI onboarding helper was not injected into /ui")

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

        replacement = root / "replacement" / "12345_A_demo_print.txt"
        replacement.parent.mkdir(parents=True, exist_ok=True)
        replacement.write_text("ForgeVault CI demo file\nChecked in replacement content.\n", encoding="utf-8")

        checkin = assert_status(
            client.post(
                f"/api/v1/records/{record_id}/checkin",
                json={
                    "actor": "ci",
                    "file_path": str(replacement),
                    "note": "CI real check-in smoke test",
                    "customer_revision": "B",
                    "internal_revision": "002",
                    "submit_for_review": True,
                    "assigned_checker": "checker@example.com",
                    "risk_level": "medium",
                },
            ),
            201,
        )

        version = checkin["file_version"]
        if version["version_number"] != 2:
            raise AssertionError(f"expected checked-in version 2, got {version}")
        if version["filename"] != replacement.name or version["original_source_path"] != str(replacement):
            raise AssertionError(f"check-in version did not use replacement file path: {version}")
        if version["customer_revision"] != "B" or version["internal_revision"] != "002":
            raise AssertionError(f"check-in revision mapping failed: {version}")
        if version["version_metadata"].get("checkin", {}).get("submitted_by") != "ci":
            raise AssertionError(f"check-in metadata missing submitter: {version}")
        if "category" not in version["version_metadata"].get("file_type", {}):
            raise AssertionError(f"check-in file type metadata missing: {version}")

        review = checkin.get("review")
        if not review or review["status"] != "pending":
            raise AssertionError(f"check-in did not create pending review: {checkin}")
        if review["file_version_id"] != version["id"]:
            raise AssertionError(f"review not tied to checked-in version: {review}")
        if review["assigned_checker"] != "checker@example.com" or review["risk_level"] != "medium":
            raise AssertionError(f"review routing failed: {review}")

        checkout_status = assert_status(client.get(f"/api/v1/records/{record_id}/checkout"))
        if checkout_status["is_checked_out"]:
            raise AssertionError(f"check-in should release checkout, got {checkout_status}")

        versions = assert_status(client.get(f"/api/v1/records/{record_id}/versions"))
        version_numbers = [item["version_number"] for item in versions]
        if version_numbers[:2] != [2, 1]:
            raise AssertionError(f"expected versions newest-first [2, 1], got {version_numbers}")

        pending = assert_status(client.get("/api/v1/reviews", params={"status_filter": "pending"}))
        if not any(item["id"] == review["id"] for item in pending):
            raise AssertionError(f"review queue did not return check-in review: {pending}")

        decided = assert_status(
            client.post(
                f"/api/v1/reviews/{review['id']}/decision",
                json={"reviewer": "checker", "decision": "approved", "comment": "CI approved checked-in version"},
            )
        )
        if decided["status"] != "approved":
            raise AssertionError(decided)

        notifications = assert_status(client.get("/api/v1/notifications"))
        event_types = {item["event_type"] for item in notifications}
        if "review.requested" not in event_types or "review.approved" not in event_types:
            raise AssertionError(f"expected review requested/approved notifications, got {notifications}")

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
