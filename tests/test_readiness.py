"""Meaningful gate regressions using an original synthetic study, not user papers."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_readiness.py"
spec = importlib.util.spec_from_file_location("check_readiness", SCRIPT)
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)
FIXTURE = ROOT / "tests" / "fixtures" / "ready-session.json"


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.state = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def assert_blocked(self, fragment):
        issues = readiness.check_readiness(self.state)
        self.assertTrue(any(fragment in issue for issue in issues), issues)

    def test_complete_record_passes_without_modification(self):
        before = copy.deepcopy(self.state)
        self.assertEqual(readiness.check_readiness(self.state), [])
        self.assertEqual(self.state, before)

    def test_blank_template_is_not_ready(self):
        template = json.loads((ROOT / "assets" / "session-template.json").read_text(encoding="utf-8"))
        self.assertTrue(readiness.check_readiness(template))

    def test_extraction_does_not_replace_reading(self):
        self.state["sources"][0]["units"][1]["status"] = "unread"
        self.assert_blocked("not fully read")

    def test_missing_inventory_check_blocks(self):
        self.state["inventory"]["confirmed"] = False
        self.assert_blocked("inventory.confirmed")

    def test_missing_supplement_check_blocks(self):
        self.state["inventory"]["supplements_checked"] = False
        self.assert_blocked("supplements_checked")

    def test_stale_identity_blocks_resume(self):
        self.state["paper"]["identity_verified"] = False
        self.assert_blocked("identity_verified")

    def test_missing_main_source_blocks(self):
        self.state["sources"][0]["availability"] = "missing"
        self.assert_blocked("required source is not available")

    def test_appendix_cannot_be_marked_optional(self):
        self.state["sources"].append({
            "id": "appendix", "role": "appendix", "required": False,
            "location": "Appendix B", "sha256": None,
            "availability": "missing", "inventory_complete": False,
            "exclusion_reason": "Too long", "exclusion_impact": "Important", "units": []
        })
        self.assert_blocked("cannot be excluded")

    def test_unavailable_supplement_blocks(self):
        self.state["sources"].append({
            "id": "supp", "role": "supplement", "required": True,
            "location": "Supplementary methods", "sha256": None,
            "availability": "blocked", "inventory_complete": False, "units": []
        })
        self.assert_blocked("required source is not available")

    def test_unread_appendix_in_same_pdf_blocks(self):
        unit = next(u for u in self.state["sources"][0]["units"] if u["id"] == "appendix-a")
        unit["status"] = "partial"
        self.assert_blocked("not fully read")

    def test_rendering_without_inspection_blocks(self):
        unit = next(u for u in self.state["sources"][0]["units"] if u["id"] == "fig1")
        unit["visual_verified"] = False
        self.assert_blocked("visual_verified")

    def test_unverified_equation_blocks(self):
        unit = next(u for u in self.state["sources"][0]["units"] if u["id"] == "eq1")
        unit["notation_verified"] = False
        self.assert_blocked("notation_verified")

    def test_critical_unresolved_question_blocks(self):
        self.state["synthesis"]["unresolved"] = [{
            "question": "Are queries paired?", "blocking": True,
            "status": "open", "note": "Would change the experiment interpretation."
        }]
        self.assert_blocked("critical question")

    def test_noncritical_uncertainty_can_remain(self):
        self.state["synthesis"]["unresolved"] = [{
            "question": "Would another window size work?", "blocking": False,
            "status": "open", "note": "Not tested; explicitly outside reported evidence."
        }]
        self.assertEqual(readiness.check_readiness(self.state), [])

    def test_missing_evidence_blocks(self):
        self.state["synthesis"]["evidence"] = []
        self.assert_blocked("grounded claim")

    def test_fabricated_evidence_locator_blocks(self):
        self.state["synthesis"]["evidence"][0]["source_ids"] = ["nonexistent-table"]
        self.assert_blocked("unknown source-unit")

    def test_segment_omission_blocks(self):
        self.state["segments"][1]["source_ids"].remove("abstract")
        self.assert_blocked("abstract is unassigned")

    def test_accidental_duplicate_ownership_blocks(self):
        self.state["segments"][2]["source_ids"].append("abstract")
        self.assert_blocked("multiple primary owners")

    def test_context_reuse_is_allowed(self):
        self.state["segments"][3]["context_ids"] = ["method", "eq1"]
        self.assertEqual(readiness.check_readiness(self.state), [])

    def test_cannot_hide_methods_as_supporting(self):
        self.state["segments"][2]["kind"] = "supporting"
        self.assert_blocked("cannot be hidden")

    def test_forward_dependency_blocks(self):
        self.state["segments"][1]["depends_on"] = ["S4"]
        self.assert_blocked("must be an earlier segment")

    def test_self_dependency_blocks(self):
        self.state["segments"][1]["depends_on"] = ["S1"]
        self.assert_blocked("must be an earlier segment")

    def test_preferences_not_yet_configured_allow_first_demonstration(self):
        self.state["preferences"]["configured"] = False
        self.state["preferences"]["setup"] = "after_first_unit"
        self.assertEqual(readiness.check_readiness(self.state), [])

    def test_unanswered_question_does_not_force_answer(self):
        self.state["progress"]["pending_question"] = "Why does the distant target get missed?"
        self.state["preferences"]["question_mode"] = "off"
        self.assertEqual(readiness.check_readiness(self.state), [])

    def test_unused_external_reference_can_be_excluded(self):
        self.state["sources"].append({
            "id": "background", "role": "external", "required": False,
            "location": "Background publication not needed for this synthetic example",
            "sha256": None, "availability": "missing", "inventory_complete": False,
            "exclusion_reason": "No argument depends on it",
            "exclusion_impact": "No claim of having read this external publication", "units": []
        })
        self.assertEqual(readiness.check_readiness(self.state), [])

    def test_unknown_progress_unit_blocks(self):
        self.state["progress"]["taught_segments"] = ["S999"]
        self.assert_blocked("unknown segment")

    def test_taught_segment_cannot_also_be_deferred(self):
        self.state["progress"]["taught_segments"] = ["S1"]
        self.state["progress"]["deferred_segments"] = ["S1"]
        self.assert_blocked("both taught and deferred: S1")

    def test_distinct_taught_and_deferred_segments_are_allowed(self):
        self.state["progress"]["taught_segments"] = ["S1"]
        self.state["progress"]["deferred_segments"] = ["S2"]
        self.assertEqual(readiness.check_readiness(self.state), [])

    def test_all_progress_conflicts_are_reported_without_mutation(self):
        self.state["progress"]["taught_segments"] = ["S2", "S1"]
        self.state["progress"]["deferred_segments"] = ["S1", "S2"]
        before = copy.deepcopy(self.state)
        issues = readiness.check_readiness(self.state)
        conflicts = [issue for issue in issues if "both taught and deferred" in issue]
        self.assertEqual(conflicts, [
            "progress: segment is both taught and deferred: S1",
            "progress: segment is both taught and deferred: S2",
        ])
        self.assertEqual(self.state, before)

    def test_cli_conflicting_progress_returns_not_ready(self):
        self.state["progress"]["taught_segments"] = ["S1"]
        self.state["progress"]["deferred_segments"] = ["S1"]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "session.json"
            path.write_text(json.dumps(self.state), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertEqual(json.loads(result.stdout)["status"], "NOT READY")

    def test_malformed_nested_values_do_not_crash(self):
        for key in ("sources", "synthesis", "segments", "preferences", "progress"):
            with self.subTest(key=key):
                state = copy.deepcopy(self.state)
                state[key] = 42
                self.assertTrue(readiness.check_readiness(state))

    def test_truthy_strings_cannot_replace_checked_flags(self):
        self.state["inventory"]["confirmed"] = "true"
        self.assert_blocked("inventory.confirmed")

    def test_cli_has_help(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("session", result.stdout)

    def test_cli_ready_machine_output(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(FIXTURE), "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result_json = json.loads(result.stdout)
        self.assertEqual(result_json["issues"], [])
        self.assertIn("does not prove", result_json["notice"])

    def test_cli_template_returns_not_ready(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(ROOT / "assets" / "session-template.json")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("NOT READY", result.stdout)

    def test_cli_missing_file_and_invalid_json_return_input_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "session.json"
            for contents in (None, "{bad", "[]", "null"):
                with self.subTest(contents=contents):
                    if contents is not None:
                        path.write_text(contents, encoding="utf-8")
                    result = subprocess.run([sys.executable, str(SCRIPT), str(path), "--json"], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(json.loads(result.stdout)["status"], "INPUT ERROR")


if __name__ == "__main__":
    unittest.main()
