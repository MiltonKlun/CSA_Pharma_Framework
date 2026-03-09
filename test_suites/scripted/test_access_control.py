"""
CSA Step 3 — Assurance Activity: Access Control Verification

Tests that role-based access control (RBAC) is enforced:
- Operators cannot approve deviations
- Only QA/Admin can close CAPAs
- Unauthenticated users are rejected
"""
import pytest
from .conftest import auth_headers


class TestUnauthenticatedAccess:
    """Verify unauthenticated requests are blocked."""

    def test_deviations_require_auth(self, client):
        resp = client.get("/deviations/")
        assert resp.status_code == 401

    def test_documents_require_auth(self, client):
        resp = client.get("/documents/")
        assert resp.status_code == 401

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/dashboard/metrics")
        assert resp.status_code == 401


class TestOperatorRestrictions:
    """Verify operators cannot perform QA/Manager actions."""

    def test_operator_cannot_approve_deviation(self, client, operator_user, db_session):
        headers = auth_headers(client, "test_operator")

        # Create deviation
        resp = client.post(
            "/deviations/",
            json={"title": "RBAC Test", "description": "Operator approval test"},
            headers=headers
        )
        dev_id = resp.json()["id"]

        # Operator tries to approve — should be forbidden
        resp = client.put(
            f"/deviations/{dev_id}/approve",
            json={"signature": {"password": "Testp@ss123", "meaning": "Trying to approve"}},
            headers=headers
        )
        assert resp.status_code == 403

    def test_operator_cannot_create_document(self, client, operator_user, db_session):
        headers = auth_headers(client, "test_operator")
        resp = client.post(
            "/documents/",
            json={"title": "Unauthorized SOP", "content": "Should fail", "version": "1.0"},
            headers=headers
        )
        assert resp.status_code == 403

    def test_operator_cannot_close_capa(self, client, operator_user, qa_user, db_session):
        """Operator cannot close a CAPA (requires QA/Admin role)."""
        op_headers = auth_headers(client, "test_operator")
        qa_headers = auth_headers(client, "test_qa")

        # QA creates a deviation first, then a CAPA
        dev_resp = client.post(
            "/deviations/",
            json={"title": "CAPA RBAC Test", "description": "Testing CAPA access"},
            headers=qa_headers
        )
        dev_id = dev_resp.json()["id"]

        capa_resp = client.post(
            "/capas/",
            json={
                "deviation_id": dev_id,
                "title": "Test CAPA",
                "description": "RBAC test",
                "assigned_to_id": operator_user.id
            },
            headers=qa_headers
        )
        capa_id = capa_resp.json()["id"]

        # Operator attempts to close the CAPA
        resp = client.put(
            f"/capas/{capa_id}/close",
            json={"signature": {"password": "Testp@ss123", "meaning": "Trying to close"}},
            headers=op_headers
        )
        assert resp.status_code == 403


class TestQAPermissions:
    """Verify QA users have the correct elevated permissions."""

    def test_qa_can_approve_deviation(self, client, operator_user, manager_user, qa_user, db_session):
        op_headers = auth_headers(client, "test_operator")
        mgr_headers = auth_headers(client, "test_manager")
        qa_headers = auth_headers(client, "test_qa")

        # Full lifecycle
        resp = client.post("/deviations/", json={"title": "QA Perm Test", "description": "QA test"}, headers=op_headers)
        dev_id = resp.json()["id"]
        client.put(f"/deviations/{dev_id}/assign", json={"assigned_to_id": operator_user.id}, headers=mgr_headers)
        client.put(f"/deviations/{dev_id}/investigate", json={"root_cause": "Root cause found"}, headers=op_headers)

        resp = client.put(
            f"/deviations/{dev_id}/approve",
            json={"signature": {"password": "Testp@ss123", "meaning": "QA approved"}},
            headers=qa_headers
        )
        assert resp.status_code == 200

    def test_qa_can_view_all_records(self, client, qa_user, db_session):
        qa_headers = auth_headers(client, "test_qa")
        assert client.get("/deviations/", headers=qa_headers).status_code == 200
        assert client.get("/documents/", headers=qa_headers).status_code == 200
        assert client.get("/batch_records/", headers=qa_headers).status_code == 200
        assert client.get("/capas/", headers=qa_headers).status_code == 200
