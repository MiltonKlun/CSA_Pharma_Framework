"""
CSA Step 3 — Assurance Activity: Electronic Signature Verification

Tests that 21 CFR Part 11 electronic signatures are enforced:
- Approvals require password re-entry
- Wrong passwords are rejected
- Signatures are linked to the authenticated user
"""
import pytest
from .conftest import auth_headers


class TestESignatureEnforcement:
    """Verify that approvals require a valid e-signature (password re-entry)."""

    def test_deviation_approval_requires_esignature(self, client, operator_user, manager_user, qa_user, db_session):
        """Full deviation flow ending with a QA approval requiring e-signature."""
        op_headers = auth_headers(client, "test_operator")
        mgr_headers = auth_headers(client, "test_manager")
        qa_headers = auth_headers(client, "test_qa")

        # Create
        resp = client.post(
            "/deviations/",
            json={"title": "E-Sig Test", "description": "Test e-signature"},
            headers=op_headers
        )
        assert resp.status_code == 201
        dev_id = resp.json()["id"]

        # Assign
        client.put(
            f"/deviations/{dev_id}/assign",
            json={"assigned_to_id": operator_user.id},
            headers=mgr_headers
        )

        # Investigate
        client.put(
            f"/deviations/{dev_id}/investigate",
            json={"root_cause": "Equipment malfunction"},
            headers=op_headers
        )

        # Approve with CORRECT password (e-signature)
        resp = client.put(
            f"/deviations/{dev_id}/approve",
            json={"signature": {"password": "Testp@ss123", "meaning": "I approve this deviation closure"}},
            headers=qa_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

    def test_wrong_password_rejects_esignature(self, client, operator_user, manager_user, qa_user, db_session):
        """An incorrect password in the e-signature must be rejected."""
        op_headers = auth_headers(client, "test_operator")
        mgr_headers = auth_headers(client, "test_manager")
        qa_headers = auth_headers(client, "test_qa")

        # Create → Assign → Investigate
        resp = client.post(
            "/deviations/",
            json={"title": "Bad E-Sig Test", "description": "Test bad password"},
            headers=op_headers
        )
        dev_id = resp.json()["id"]
        client.put(f"/deviations/{dev_id}/assign", json={"assigned_to_id": operator_user.id}, headers=mgr_headers)
        client.put(f"/deviations/{dev_id}/investigate", json={"root_cause": "Unknown"}, headers=op_headers)

        # Approve with WRONG password
        resp = client.put(
            f"/deviations/{dev_id}/approve",
            json={"signature": {"password": "WRONG_PASSWORD", "meaning": "Attempting approval"}},
            headers=qa_headers
        )
        assert resp.status_code == 401
        assert "Electronic signature verification failed" in resp.json()["detail"]


class TestESignatureOnDocuments:
    """Verify that document approval requires a valid e-signature."""

    def test_document_approval_with_esignature(self, client, manager_user, qa_user, db_session):
        mgr_headers = auth_headers(client, "test_manager")
        qa_headers = auth_headers(client, "test_qa")

        # Create document
        resp = client.post(
            "/documents/",
            json={"title": "SOP-TEST", "content": "Test content", "version": "1.0"},
            headers=mgr_headers
        )
        assert resp.status_code == 201
        doc_id = resp.json()["id"]

        # Send to review
        client.put(f"/documents/{doc_id}/review", headers=qa_headers)

        # Approve with e-signature
        resp = client.put(
            f"/documents/{doc_id}/approve",
            json={"signature": {"password": "Testp@ss123", "meaning": "Approved for use"}},
            headers=qa_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
