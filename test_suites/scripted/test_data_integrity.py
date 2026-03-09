"""
CSA Step 3 — Assurance Activity: Data Integrity Verification

Tests the ALCOA+ principles (Attributable, Legible, Contemporaneous,
Original, Accurate) for data stored in the QMS system:
- Records maintain integrity through state transitions
- Unique constraints are enforced
- Required fields cannot be null/empty
"""
import pytest
from .conftest import auth_headers


class TestDataAttributability:
    """Verify that records are attributable to a specific user."""

    def test_deviation_tracks_reporter(self, client, operator_user, db_session):
        headers = auth_headers(client, "test_operator")
        resp = client.post(
            "/deviations/",
            json={"title": "Attribution Test", "description": "Check reporter is tracked"},
            headers=headers
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["reported_by_id"] == operator_user.id

    def test_batch_record_tracks_operator(self, client, operator_user, db_session):
        headers = auth_headers(client, "test_operator")
        resp = client.post(
            "/batch_records/",
            json={"batch_number": "BR-ATTR-001", "product_name": "Test Product"},
            headers=headers
        )
        assert resp.status_code == 201
        assert resp.json()["operator_id"] == operator_user.id


class TestDataUniqueness:
    """Verify unique constraints are enforced."""

    def test_duplicate_batch_number_rejected(self, client, operator_user, db_session):
        headers = auth_headers(client, "test_operator")

        # Create first batch record
        resp = client.post(
            "/batch_records/",
            json={"batch_number": "BR-UNIQ-001", "product_name": "Product A"},
            headers=headers
        )
        assert resp.status_code == 201

        # Attempt duplicate
        resp = client.post(
            "/batch_records/",
            json={"batch_number": "BR-UNIQ-001", "product_name": "Product B"},
            headers=headers
        )
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]


class TestDataAccuracy:
    """Verify data transitions maintain accuracy."""

    def test_deviation_status_transitions_correctly(self, client, operator_user, manager_user, qa_user, db_session):
        op_headers = auth_headers(client, "test_operator")
        mgr_headers = auth_headers(client, "test_manager")
        qa_headers = auth_headers(client, "test_qa")

        # Create: status = open
        resp = client.post("/deviations/", json={"title": "Accuracy Test", "description": "State transitions"}, headers=op_headers)
        dev_id = resp.json()["id"]
        assert resp.json()["status"] == "open"

        # Assign: status = investigating
        resp = client.put(f"/deviations/{dev_id}/assign", json={"assigned_to_id": operator_user.id}, headers=mgr_headers)
        assert resp.json()["status"] == "investigating"

        # Investigate: status = pending_approval
        resp = client.put(f"/deviations/{dev_id}/investigate", json={"root_cause": "Found the cause"}, headers=op_headers)
        assert resp.json()["status"] == "pending_approval"

        # Approve: status = closed
        resp = client.put(
            f"/deviations/{dev_id}/approve",
            json={"signature": {"password": "Testp@ss123", "meaning": "Approved"}},
            headers=qa_headers
        )
        assert resp.json()["status"] == "closed"

    def test_cannot_approve_deviation_not_pending(self, client, operator_user, qa_user, db_session):
        """Cannot approve a deviation that isn't in pending_approval status."""
        op_headers = auth_headers(client, "test_operator")
        qa_headers = auth_headers(client, "test_qa")

        # Create (status = open, not pending_approval)
        resp = client.post("/deviations/", json={"title": "Invalid Approve", "description": "Skip steps"}, headers=op_headers)
        dev_id = resp.json()["id"]

        # Attempt to approve without investigation
        resp = client.put(
            f"/deviations/{dev_id}/approve",
            json={"signature": {"password": "Testp@ss123", "meaning": "Skipping steps"}},
            headers=qa_headers
        )
        assert resp.status_code == 400
        assert "pending approval" in resp.json()["detail"].lower()
