"""
Comprehensive End-to-End Test Suite for Capstone FinTech Platform
Executes unit tests, validation checks, and operational gate validations.
"""
import unittest
import os
import sys

# Ensure local backend module import
sys.path.insert(0, os.path.dirname(__file__))
from main import (
    liveness_probe, readiness_probe, process_settlement, 
    TransactionPayload, metrics, app
)
from fastapi import HTTPException

class TestCapstoneFintechCore(unittest.TestCase):

    def test_01_liveness_probe(self):
        result = liveness_probe()
        self.assertEqual(result["status"], "ALIVE")
        self.assertIn("timestamp", result)

    def test_02_readiness_healthy(self):
        os.environ["DB_ONLINE"] = "true"
        os.environ["VAULT_SECRETS_MOUNTED"] = "true"
        result = readiness_probe()
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["version"], "3.0.0")

    def test_03_readiness_degraded_db_failure(self):
        os.environ["DB_ONLINE"] = "false"
        with self.assertRaises(HTTPException) as cm:
            readiness_probe()
        self.assertEqual(cm.exception.status_code, 503)
        os.environ["DB_ONLINE"] = "true" # Reset

    def test_04_payment_settlement_valid(self):
        tx = TransactionPayload(
            account_id="ACC-CORP-9921",
            destination_routing="ROUT-US-1029",
            amount=2500.50,
            currency="USD",
            idempotency_key="IDEMP-UNIQUE-883311"
        )
        res = process_settlement(tx)
        self.assertEqual(res["status"], "CLEARED_AND_SETTLED")
        self.assertEqual(res["amount"], 2500.50)
        self.assertIn("SETTLE-ACC-CORP-9921-", res["settlement_id"])

    def test_05_payment_settlement_aml_compliance_breach(self):
        # Exceeds $500,000 threshold
        tx = TransactionPayload(
            account_id="ACC-SUSPICIOUS-01",
            destination_routing="ROUT-OFFSHORE-01",
            amount=9999999.00,
            currency="USD",
            idempotency_key="IDEMP-HIGH-VALUE-99"
        )
        with self.assertRaises(HTTPException) as cm:
            process_settlement(tx)
        self.assertEqual(cm.exception.status_code, 403)
        self.assertIn("AML volume compliance limit exceeded", cm.exception.detail)

    def test_06_metrics_telemetry_endpoint(self):
        res = metrics()
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"http_requests_total", res.body)

if __name__ == "__main__":
    unittest.main()
