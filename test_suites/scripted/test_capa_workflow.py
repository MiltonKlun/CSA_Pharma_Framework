"""
CSA Step 3 — Assurance Activity: CAPA Workflow Lifecycle

End-to-end scripted test covering the full CAPA lifecycle:
Create (linked to deviation) → Implement → Effectiveness Check → Close

This is a supporting feature but requires scripted testing due to data integrity impact.
"""
import pytest
from .conftest import auth_headers


class TestCAPAFullLifecycle:
    """Complete happy-path CAPA lifecycle."""

    def test_full_capa_lifecycle(self, client, operator_user, qa_user, db_session):
        op_headers = auth_headers(client, "test_operator")
        qa_headers = auth_headers(client, "test_qa")

        # Prerequisite: Create a deviation to link the CAPA to
        dev_resp = client.post(
            "/deviations/",
            json={"title": "CAPA Parent Deviation", "description": "Deviation triggering CAPA"},
            headers=op_headers
        )
        assert dev_resp.status_code == 201
        dev_id = dev_resp.json()["id"]

        # Step 1: QA creates CAPA linked to the deviation
        resp = client.post(
            "/capas/",
            json={
                "deviation_id": dev_id,
                "title": "CAPA-LIFECYCLE-001",
                "description": "Replace faulty thermostat sensors",
                "assigned_to_id": operator_user.id
            },
            headers=qa_headers
        )
        assert resp.status_code == 201
        capa = resp.json()
        capa_id = capa["id"]
        assert capa["status"] == "open"
        assert capa["deviation_id"] == dev_id

        # Step 2: Assignee implements the CAPA
        resp = client.put(
            f"/capas/{capa_id}/implement",
            json={"implementation_notes": "Replaced 3 thermostat sensors in cold room units"},
            headers=op_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "implemented"

        # Step 3: QA checks effectiveness
        resp = client.put(
            f"/capas/{capa_id}/check_effectiveness",
            json={"check_notes": "Temperature stable for 30 days post-replacement"},
            headers=qa_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "effectiveness_check"

        # Step 4: QA closes CAPA with e-signature
        resp = client.put(
            f"/capas/{capa_id}/close",
            json={"signature": {"password": "Testp@ss123", "meaning": "CAPA effectiveness confirmed. Closing."}},
            headers=qa_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"
        assert resp.json()["closed_at"] is not None


class TestCAPAValidation:
    """Edge cases and validation rules."""

    def test_capa_requires_existing_deviation(self, client, qa_user, db_session):
        """CAPA must be linked to a valid deviation."""
        qa_headers = auth_headers(client, "test_qa")
        resp = client.post(
            "/capas/",
            json={
                "deviation_id": 99999,
                "title": "Orphan CAPA",
                "description": "No parent deviation",
                "assigned_to_id": qa_user.id
            },
            headers=qa_headers
        )
        assert resp.status_code == 404
        assert "deviation not found" in resp.json()["detail"].lower()

    def test_cannot_close_unimplemented_capa(self, client, operator_user, qa_user, db_session):
        """Cannot close a CAPA that hasn't been through effectiveness check."""
        op_headers = auth_headers(client, "test_operator")
        qa_headers = auth_headers(client, "test_qa")

        # Create deviation + CAPA
        dev_resp = client.post("/deviations/", json={"title": "Skip Test Dev", "description": "Test"}, headers=op_headers)
        dev_id = dev_resp.json()["id"]

        capa_resp = client.post(
            "/capas/",
            json={"deviation_id": dev_id, "title": "Skip CAPA", "description": "Test", "assigned_to_id": operator_user.id},
            headers=qa_headers
        )
        capa_id = capa_resp.json()["id"]

        # Try to close directly (skipping implement + effectiveness)
        resp = client.put(
            f"/capas/{capa_id}/close",
            json={"signature": {"password": "Testp@ss123", "meaning": "Trying to skip"}},
            headers=qa_headers
        )
        assert resp.status_code == 400
