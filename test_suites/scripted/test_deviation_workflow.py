"""
CSA Step 3 — Assurance Activity: Deviation Workflow Lifecycle

End-to-end scripted test covering the full deviation lifecycle:
Create → Assign → Investigate → Approve/Close

This is a HIGH risk feature requiring scripted testing.
"""
import pytest
from .conftest import auth_headers


class TestDeviationFullLifecycle:
    """Complete happy-path deviation lifecycle."""

    def test_full_deviation_lifecycle(self, client, operator_user, manager_user, qa_user, db_session):
        op_headers = auth_headers(client, "test_operator")
        mgr_headers = auth_headers(client, "test_manager")
        qa_headers = auth_headers(client, "test_qa")

        # Step 1: Operator reports a deviation
        resp = client.post(
            "/deviations/",
            json={"title": "DEV-LIFECYCLE-001", "description": "Temperature excursion in cold room"},
            headers=op_headers
        )
        assert resp.status_code == 201
        dev = resp.json()
        dev_id = dev["id"]
        assert dev["status"] == "open"
        assert dev["reported_by_id"] == operator_user.id

        # Step 2: Manager assigns deviation for investigation
        resp = client.put(
            f"/deviations/{dev_id}/assign",
            json={"assigned_to_id": operator_user.id},
            headers=mgr_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "investigating"
        assert resp.json()["assigned_to_id"] == operator_user.id

        # Step 3: Assignee completes investigation
        resp = client.put(
            f"/deviations/{dev_id}/investigate",
            json={"root_cause": "Faulty thermostat sensor in unit #3"},
            headers=op_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending_approval"

        # Step 4: QA approves with e-signature
        resp = client.put(
            f"/deviations/{dev_id}/approve",
            json={"signature": {"password": "Testp@ss123", "meaning": "Deviation investigation complete and satisfactory"}},
            headers=qa_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"
        assert resp.json()["qa_approval_id"] == qa_user.id
        assert resp.json()["closed_at"] is not None

    def test_deviation_visible_in_list(self, client, operator_user, db_session):
        """Created deviations appear in the list endpoint."""
        headers = auth_headers(client, "test_operator")
        client.post("/deviations/", json={"title": "List Test", "description": "Should appear"}, headers=headers)

        resp = client.get("/deviations/", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_deviation_get_by_id(self, client, operator_user, db_session):
        """Created deviation can be retrieved by ID."""
        headers = auth_headers(client, "test_operator")
        create_resp = client.post(
            "/deviations/",
            json={"title": "Get By ID Test", "description": "Retrieve by ID"},
            headers=headers
        )
        dev_id = create_resp.json()["id"]

        resp = client.get(f"/deviations/{dev_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get By ID Test"

    def test_nonexistent_deviation_returns_404(self, client, operator_user, db_session):
        headers = auth_headers(client, "test_operator")
        resp = client.get("/deviations/99999", headers=headers)
        assert resp.status_code == 404
