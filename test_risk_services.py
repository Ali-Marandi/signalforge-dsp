from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from signalforge_finance import LocalRiskEngine, RiskConfig
from signalforge_studio.risk_services import (
    RiskResearchRequest,
    calculate_risk,
    export_risk_manifest,
    extract_decimal_returns,
    preview_return_file,
)


class RiskServicesTests(unittest.TestCase):
    def _write_returns_file(self, directory: Path) -> Path:
        path = directory / "local_returns.csv"
        rows = ["date,return_pct"]
        rows.extend(f"2026-01-{index + 1:02d},{((index % 11) - 5) / 10:.1f}" for index in range(30))
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    def _request(self) -> RiskResearchRequest:
        return RiskResearchRequest(
            method="normal_monte_carlo",
            confidence_level=0.90,
            min_observations=30,
            simulation_count=1_000,
            random_seed=17,
            return_column="return_pct",
            return_unit="percent",
        )

    def test_preview_requires_explicit_return_unit_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            preview = preview_return_file(self._write_returns_file(Path(directory)))
        self.assertEqual(preview.headers, ("date", "return_pct"))
        decimal = extract_decimal_returns(preview, column="return_pct", unit="decimal")
        percent = extract_decimal_returns(preview, column="return_pct", unit="percent")
        self.assertAlmostEqual(decimal[0], -0.5)
        self.assertAlmostEqual(percent[0], -0.005)

    def test_calculation_matches_public_engine_for_same_input_and_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            preview = preview_return_file(self._write_returns_file(Path(directory)))
        request = self._request()
        run = calculate_risk(preview, request, research_use_acknowledged=True)
        expected = LocalRiskEngine(RiskConfig(0.90, 30, 1_000, 17)).normal_monte_carlo(
            extract_decimal_returns(preview, column="return_pct", unit="percent")
        )
        self.assertEqual(run.estimate, expected)
        self.assertEqual(run.source_row_count, 30)
        self.assertTrue(run.research_use_acknowledged)

    def test_research_acknowledgement_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            preview = preview_return_file(self._write_returns_file(Path(directory)))
        with self.assertRaisesRegex(ValueError, "Acknowledge research-only use"):
            calculate_risk(preview, self._request(), research_use_acknowledged=False)

    def test_manifest_preserves_provenance_but_excludes_raw_returns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "risk_run.json"
            preview = preview_return_file(self._write_returns_file(Path(directory)))
            run = calculate_risk(preview, self._request(), research_use_acknowledged=True)
            export_risk_manifest(run, destination, application_version="1.2.0")
            payload = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(payload["source"]["return_unit"], "percent")
        self.assertEqual(payload["source"]["unit_transform"], "divide_by_100")
        self.assertEqual(payload["configuration"]["random_seed"], 17)
        self.assertFalse(payload["governance"]["raw_return_values_included"])
        self.assertNotIn("returns", payload)
        self.assertNotIn("data_rows", payload)

    def test_missing_return_value_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.csv"
            rows = ["date,return"]
            rows.extend(f"2026-02-{index + 1:02d},0.01" for index in range(29))
            rows.append("2026-03-01,")
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            preview = preview_return_file(path)
        with self.assertRaisesRegex(ValueError, "missing value"):
            extract_decimal_returns(preview, column="return", unit="decimal")


if __name__ == "__main__":
    unittest.main()
