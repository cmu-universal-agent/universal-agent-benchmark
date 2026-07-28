"""Offline proof that the LangGraph retail wrapper satisfies WS3 contract evidence."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_ws3_tau_retail_contract.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frameworks.langgraph_agent.retail_evidence import build_wrapper_evidence


class TestLangGraphRetailWrapperEvidence(unittest.TestCase):
    def test_langgraph_wrapper_evidence_passes_contract_validator(self) -> None:
        evidence = build_wrapper_evidence()
        self.assertEqual(evidence["framework"], "langgraph")

        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "wrapper_evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--wrapper-evidence", str(evidence_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WS3_TAU_RETAIL_CONTRACT_OK", result.stdout)
        self.assertIn("wrapper_evidence=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
