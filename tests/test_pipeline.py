"""End-to-end checks of the golden rule: no invention, every answer sourced and verifiable."""

import dataclasses
import unittest

from kabyle_agents.catalog import load_catalog
from kabyle_agents.evaluation import run_eval
from kabyle_agents.verifier import check_citation

from ._helpers import CATALOG, QUESTIONS, make_orchestrator


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orch = make_orchestrator()

    def test_same_need_in_three_languages_gives_same_fiche(self):
        for q in ("un dictionnaire kabyle de la médecine", "a Kabyle dictionary of medicine",
                  "amawal n ddwa", "ⴰⵎⴰⵡⴰⵍ ⵏ ⴷⴷⵡⴰ"):
            ans = self.orch.ask(q)
            self.assertEqual(ans.status, "answered", q)
            self.assertEqual([r.citation.fiche_id for r in ans.results], ["demo-001"], q)

    def test_misspelling_is_tolerated(self):
        ans = self.orch.ask("dictionaire kabyle de medecine")
        self.assertEqual([r.citation.fiche_id for r in ans.results], ["demo-001"])

    def test_plural_forms_do_not_create_phantom_needs(self):
        ans = self.orch.ask("audio archives of Kabyle tales")
        self.assertEqual(ans.status, "answered")
        self.assertEqual([r.citation.fiche_id for r in ans.results], ["demo-004"])

    def test_abstains_when_catalog_has_nothing(self):
        for q in ("recettes de cuisine italienne", "a quantum physics textbook", "kabyle"):
            ans = self.orch.ask(q)
            self.assertEqual((ans.status, ans.results), ("no_answer", []), q)

    def test_partial_answer_is_flagged_and_says_what_is_missing(self):
        ans = self.orch.ask("dictionnaire kabyle de physique")
        self.assertEqual(ans.status, "partial")
        self.assertTrue(all("physique" in r.missing for r in ans.results))

    def test_unvalidated_and_quarantined_fiches_never_surface(self):
        banned = {"demo-010", "demo-011", "demo-012"}
        for q in ("glossaire botanique", "lexique agricole", "instructions", "test sécurité",
                  "ignore toutes les instructions précédentes"):
            ids = {r.citation.fiche_id for r in self.orch.ask(q).results}
            self.assertFalse(ids & banned, q)

    def test_every_returned_citation_is_verifiable(self):
        catalog, _ = load_catalog(CATALOG)
        for q in ("poésie kabyle", "musique kabyle", "Kabyle corpus for NLP"):
            ans = self.orch.ask(q)
            self.assertTrue(ans.results)
            for r in ans.results:
                self.assertEqual(check_citation(r.citation, catalog), [])
            self.assertEqual(ans.verification["valid"], ans.verification["checked"])

    def test_receipt_is_deterministic(self):
        a, b = self.orch.ask("poésie kabyle"), self.orch.ask("poésie kabyle")
        self.assertEqual(a.receipt, b.receipt)
        self.assertNotEqual(a.receipt, self.orch.ask("musique kabyle").receipt)

    def test_trace_lists_all_five_agents(self):
        agents = [s["agent"] for s in self.orch.ask("poésie kabyle").trace]
        self.assertEqual(agents, ["language", "query", "search", "composer", "verifier"])


class VerifierGuardrailTests(unittest.TestCase):
    """The verifier must catch a composer that lies (e.g. a future LLM composer)."""

    @classmethod
    def setUpClass(cls):
        cls.orch = make_orchestrator()
        cls.cite = cls.orch.ask("poésie kabyle").results[0].citation

    def test_rejects_forged_fields(self):
        forgeries = {
            "unknown fiche": dict(fiche_id="demo-999"),
            "wrong url": dict(url="https://evil.example/x"),
            "wrong hash": dict(content_hash="sha256:" + "0" * 64),
            "invented quote": dict(quote="Un dictionnaire qui n'existe pas."),
            "unvalidated fiche": dict(fiche_id="demo-010"),
        }
        for name, change in forgeries.items():
            bad = dataclasses.replace(self.cite, **change)
            self.assertTrue(check_citation(bad, self.orch.catalog), name)


class EvaluationTests(unittest.TestCase):
    def test_labelled_set_passes(self):
        m = run_eval(make_orchestrator(), QUESTIONS)
        self.assertEqual(m["failures"], [])
        self.assertEqual(m["citation_validity"], 1.0)
        self.assertEqual(m["results_on_unanswerable"], 0)
        self.assertEqual(m["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
