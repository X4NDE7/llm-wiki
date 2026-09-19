"""Deterministic contract tests. Fixtures are not Jev accuracy evaluations."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wiki_ingest.cli import main
from wiki_ingest.evidence import align, navigate, packet
from wiki_ingest.jev import Jev, choice, noul, score
from wiki_ingest.source import annotate, prepare, validate_index


def response(body, overrides=None):
    answers = {}
    for key, question in body["questions"].items():
        kind = question["type"]
        value = (overrides or {}).get(key)
        if kind == "noul":
            answers[key] = {"type": kind, "noul": 0.1 if value is None else value}
        elif kind == "choice":
            selected = value or ("unknown" if "unknown" in question["criteria"] else next(iter(question["criteria"])))
            answers[key] = {"type": kind, "choice": selected, "confidence": 1,
                            "probabilities": {k: float(k == selected) for k in question["criteria"]}}
        else:
            selected = 0 if value is None else value
            answers[key] = {"type": kind, "score": selected, "confidence": 1,
                            "legend": {str(i): v for i, v in enumerate(question["criteria"])},
                            "probabilities": {str(i): float(i == selected) for i in range(len(question["criteria"]))}}
    return {"model": "fixture-only", "answers": answers, "usage": {"input_tokens": 1, "output_tokens": 1}}


def live(overrides=None):
    return Jev(live=True, transport=lambda body: response(body, overrides))


def source(source_id="book", lines=None):
    return {"source_id": source_id, "title": "Synthetic Test Book", "edition": "test",
            "uri": "fixtures/book.txt", "pages": [{"page": "xii", "lines": lines or [
                {"text": "# Attention", "kind": "heading"},
                {"text": "Attention is the selection", "bbox": [0, 0, 200, 20], "region": "main"},
                {"text": "of a target for processing.", "bbox": [0, 20, 200, 40], "region": "main"}]}]}


class IngestionTests(unittest.TestCase):
    def test_offline_retains_unresolved_text_and_boundaries(self):
        jev = Jev()
        index = prepare(source(), jev)
        self.assertEqual(len(index["blocks"]), 3)
        self.assertEqual(index["boundaries"][0]["decision"]["label"], "unresolved")
        self.assertTrue(all(r["status"] == "pending" for r in jev.records))
        self.assertEqual(validate_index(index), index)

    def test_join_preserves_exact_quote_coordinates_and_identity(self):
        index = prepare(source(), live({"1": 0.95, "kind": "paragraph"}))
        block = index["blocks"][1]
        self.assertEqual(len(index["blocks"]), 2)
        self.assertEqual(block["text"], "Attention is the selection of a target for processing.")
        self.assertEqual(block["original_text"], "Attention is the selection\nof a target for processing.")
        self.assertEqual(block["spans"][0]["bbox"], [0, 0, 200, 20])
        self.assertEqual(block["spans"][0]["page"], "xii")
        validate_index(index)
        revised = source()
        revised["edition"] = "changed"
        self.assertNotEqual(block["id"], prepare(revised, live({"1": 0.95}))["blocks"][1]["id"])

    def test_explicit_boundaries_and_fences_never_join(self):
        lines = [{"text": "sentence", "region": "left"}, {"text": "continuation", "region": "right"},
                 {"text": "new paragraph", "region": "right", "break_before": True},
                 {"text": ""}, {"text": "```python"}, {"text": "x = 1"}, {"text": "```"},
                 {"text": "- list item"}, {"text": "# Heading"}]
        jev = live()
        index = prepare(source(lines=lines), jev)
        self.assertEqual(index["boundaries"], [])
        self.assertEqual([b["kind"] for b in index["blocks"]][3:6], ["code"] * 3)

    def test_changed_index_cannot_supply_evidence(self):
        index = prepare(source(), Jev())
        index["blocks"][1]["original_text"] = "Invented quote"
        with self.assertRaises(ValueError):
            packet([index], {"id": "task", "question": "Attention?"}, Jev())

    def test_dimension_revisions_preserve_previous_answers_and_questions(self):
        dims = {"version": "v1", "questions": {"operation": noul("Does passage state an operation?")}}
        index = annotate(prepare(source(), Jev()), dims, live({"operation": 0.9}))
        old = index["dimension_digest"]
        dims["questions"]["operation"]["instructions"] = "Does passage explicitly describe an operation?"
        revised = annotate(index, dims, Jev())
        self.assertNotEqual(old, revised["dimension_digest"])
        self.assertEqual(len(revised["annotation_history"]), 2)
        self.assertEqual(revised["blocks"][0]["annotations"][old]["operation"]["label"], "yes")
        self.assertIn(old, revised["dimension_sets"])

    def test_no_answer_choice_does_not_manufacture_evidence(self):
        index = prepare(source(), Jev())
        result = packet([index], {"id": "missing", "question": "What is the price of a telescope?"}, live())
        self.assertEqual(result["answer_status"], "absent_in_candidates")
        self.assertTrue(all(s["selected_id"] is None for s in result["selections"]))
        self.assertEqual(len(result["low_relevance_candidates"]), 3)

    def test_conflicts_and_uncertainty_survive_low_relevance(self):
        index = prepare(source(), Jev())
        result = packet([index], {"id": "conflict", "question": "Attention is involuntary?"},
                        live({"conflicting_accounts": 0.95, "usable": 0.5}))
        self.assertEqual(len(result["roles"]["conflicting_accounts"]), 3)
        self.assertEqual(len(result["uncertain_candidates"]), 3)
        self.assertFalse(result["instruction_flags"])
        original = {block["id"]: block["original_text"] for block in index["blocks"]}
        for candidate in result["candidates"]:
            self.assertEqual(candidate["evidence"]["quote"], original[candidate["evidence"]["block_id"]])

    def test_explicit_candidates_and_dimensions_expand_shortlist(self):
        dims = {"version": "v1", "questions": {"operation": noul("Does passage describe an operation?")}}
        index = annotate(prepare(source(), Jev()), dims, live({"operation": 0.95}))
        result = packet([index], {"id": "task", "question": "Nothing lexical", "dimension_filters": {"operation": "yes"}}, Jev(), 1)
        self.assertEqual(result["coverage"]["evaluated_candidates"], 3)
        self.assertEqual(result["answer_status"], "unresolved")
        self.assertEqual(result["coverage"]["omitted_ids"], [])
        with self.assertRaises(ValueError):
            packet([index], {"id": "task", "question": "q", "candidate_ids": ["invented"]}, Jev())

    def test_entity_alignment_never_merges(self):
        a, b = prepare(source("a"), Jev()), prepare(source("b"), Jev())
        pair = {"kind": "concept", "left": [a["blocks"][1]["id"]], "right": [b["blocks"][1]["id"]]}
        result = align([a, b], pair, live({"relationship": 2}))
        self.assertEqual(result["relationship"], "candidate_same")
        self.assertFalse(result["merge_allowed"])
        self.assertEqual(result["evidence"]["left"][0]["source_id"], "a")

    def test_navigation_preserves_two_paths_and_independent_facets(self):
        def distribution(body):
            result = response(body)
            result["answers"]["branch"] = {"type": "choice", "choice": "a", "confidence": 0.1,
                                            "probabilities": {"a": 0.55, "b": 0.45, "none": 0}}
            return result
        nodes = [{"id": "a", "description": "Mechanism A"}, {"id": "b", "description": "Mechanism B"}]
        result = navigate("Synthetic concept", {"mechanism": nodes, "application": nodes},
                          Jev(live=True, transport=distribution), width=2)
        self.assertEqual(len(result["facets"]["mechanism"]["paths"]), 2)
        self.assertIn("application", result["facets"])
        offline = navigate("Synthetic concept", {"mechanism": nodes}, Jev())
        self.assertEqual(len(offline["facets"]["mechanism"]["unresolved"]), 1)

    def test_client_rejects_malformed_answers_and_budget_overflow(self):
        jev = Jev(live=True, transport=lambda body: {"model": "bad", "answers": {}})
        decision = jev.ask("source", {"q": noul("Is it explicit?")})["q"]
        self.assertEqual(decision["status"], "invalid_response")
        self.assertEqual(decision["label"], "unresolved")
        oversized = Jev().ask("x" * 25000, {"q": noul("Is it explicit?")})["q"]
        self.assertEqual(oversized["status"], "oversized")
        exhausted = Jev(live=True, transport=response, max_requests=1)
        exhausted.ask("one", {"q": noul("Is it explicit?")})
        self.assertEqual(exhausted.ask("two", {"q": noul("Is it explicit?")})["q"]["status"], "budget_exhausted")

    def test_bad_distributions_and_relative_score_are_validated(self):
        questions = {"rating": score("How directly does this answer?", ["None", "Partial", "Direct"])}
        def invalid(body):
            result = response(body, {"rating": 2})
            result["answers"]["rating"]["score"] = 0.99
            return result
        self.assertEqual(Jev(live=True, transport=invalid).ask("data", questions)["rating"]["status"], "invalid_response")
        self.assertEqual(live({"rating": 2}).ask("data", questions)["rating"]["answer"]["score"], 2)
        with self.assertRaises(ValueError):
            Jev().ask("data", {"q": choice("Pick", {str(i): "option" for i in range(256)})})

    def test_replay_is_bound_to_exact_state_questions_and_model(self):
        original = live({"q": 0.95})
        questions = {"q": noul("Explicit?")}
        original.ask("data", questions)
        replay = Jev(replay=original.audit())
        self.assertEqual(replay.ask("data", questions)["q"]["label"], "yes")
        self.assertEqual(replay.ask("changed data", questions)["q"]["label"], "unresolved")
        broken = copy.deepcopy(original.audit())
        broken["requests"][0]["request"]["state"] = "wrong"
        self.assertEqual(Jev(replay=broken).ask("data", questions)["q"]["status"], "invalid_replay")

    def test_cli_preserves_existing_output_and_defaults_to_offline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, output = root / "input.json", root / "index.json"
            path.write_text(json.dumps(source()), encoding="utf-8")
            with patch("builtins.print"):
                self.assertEqual(main(["prepare", str(path), "--output", str(output)]), 0)
                original = output.read_bytes()
                self.assertEqual(main(["prepare", str(path), "--output", str(output)]), 1)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(json.loads(Path(str(output) + ".run.json").read_text())["mode"], "offline")


if __name__ == "__main__":
    unittest.main()
