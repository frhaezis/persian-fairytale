"""Regression checks for the authored V2 teaching contract and numerical examples.

These tests catch missing explanations/links and invalid examples. They do not
claim human comprehension, observed learning duration, or independently prove
that every prose explanation is pedagogically sufficient; see manual audit.
"""
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DesktopTeachingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'data/curriculum.json').read_text())
        cls.missions = {m['id']: m for m in cls.data['missions']}
        cls.exercises = json.loads((ROOT / 'data/exercise_teaching.json').read_text())

    def text(self, mid):
        return json.dumps(self.missions[mid]['teaching'], ensure_ascii=False).lower()

    def linked_text(self, mid, target):
        t = self.missions[mid]['teaching']
        entry = next(x for x in t['assessmentMap'] if x['target'] == target)
        steps = {s['id']: s for s in t['steps']}
        return json.dumps([steps[sid] for sid in entry['taughtBy']], ensure_ascii=False).lower()

    def test_all_forty_have_prerequisites_method_and_specific_bridge(self):
        self.assertEqual(set(self.missions), {f'm{i:02}' for i in range(1, 41)})
        goals, bridges = set(), set()
        for mid, m in self.missions.items():
            with self.subTest(mission=mid):
                t = m['teaching']
                self.assertEqual(m['pedagogyVersion'], 2)
                for key in ['goal', 'taskBridge', 'interview']:
                    self.assertTrue(t[key].strip())
                self.assertEqual(t['goal'], m['objective'])
                self.assertTrue(t['prerequisites'])
                self.assertTrue(all(p['name'] and p['explanation'] for p in t['prerequisites']))
                self.assertTrue(all(s['title'] and s['text'] for s in t['steps']))
                self.assertEqual(len({s['id'] for s in t['steps']}), len(t['steps']))
                self.assertTrue(all(s['id'].startswith(mid + '-s') for s in t['steps']))
                self.assertGreaterEqual(len(t['workedExample']['steps']), 3)
                self.assertTrue(all(p['symptom'] and p['explanation'] for p in t['pitfalls']))
                goals.add(t['goal']); bridges.add(t['taskBridge'])
        self.assertEqual(len(goals), 40)
        self.assertEqual(len(bridges), 40)
        self.assertEqual({m['npc'] for m in self.missions.values()}, {'Лейла', 'Сафар', 'Нур'})

    def test_every_assessment_and_choice_has_resolvable_teaching(self):
        for mid, m in self.missions.items():
            with self.subTest(mission=mid):
                t = m['teaching']; refs = {s['id'] for s in t['steps']}
                mapping = {e['target']: e for e in t['assessmentMap']}
                self.assertEqual(len(mapping), len(t['assessmentMap']))
                expected = {'activity', 'check', 'transfer'}
                a = m['activity']
                key = {'compare': 'cards', 'retrieval': 'documents', 'split': 'records', 'agent': 'steps'}.get(a['type'])
                if key:
                    expected.update(f'activity.{key}.{i}' for i in range(len(a[key])))
                expected.update(f'topics.{i}.question' for i in range(len(m['topics'])))
                self.assertEqual(set(mapping), expected)
                for target, entry in mapping.items():
                    self.assertTrue(entry['taughtBy'], target)
                    self.assertTrue(set(entry['taughtBy']).issubset(refs), target)
                    self.assertTrue(entry['rationale'], target)

    def test_code_missions_have_matching_complete_api_tutorials(self):
        used = set()
        # The exercise registry is a dictionary keyed by the actual exercise ID.
        for m in self.missions.values():
            a = m['activity']
            if a['type'] != 'code':
                continue
            eid = a['exerciseId']; used.add(eid)
            self.assertIn(eid, self.exercises)
            t = self.exercises[eid]
            for field in ['goal', 'prerequisites', 'steps', 'workedExample', 'taskBridge', 'pitfalls', 'interview']:
                self.assertTrue(t[field], (eid, field))
            self.assertIn(eid, json.dumps(m['activity']))
        self.assertEqual(len(used), 16)
        self.assertEqual(len(self.exercises), 20)

    def test_difficult_checks_link_to_the_facts_needed_to_answer(self):
        # These requirements protect against a question being retained while its
        # causal explanation is removed or the link points at an unrelated step.
        needed = {
            ('m01', 'transfer'): ['self-supervised', 'данных'],
            ('m05', 'transfer'): ['w1', 'x²', 'параметр'],
            ('m09', 'check'): ['variance', 'целевого ответа'],
            ('m15', 'transfer'): ['contrastive', 'пар'],
            ('m17', 'check'): ['eval', 'no_grad', 'autograd'],
            ('m19', 'check'): ['train', 'eval', 'стенд'],
            ('m22', 'check'): ['q', 'k', 'v', 'сохранятся'],
            ('m25', 'check'): ['накоп', 'не меньше', 'перенорм'],
            ('m28', 'transfer'): ['тип', 'разрешени'],
            ('m31', 'check'): ['прежнюю позицию', 'бюджет'],
            ('m32', 'transfer'): ['не', 'личность модели', 'success'],
            ('m37', 'check'): ['latency', 'throughput', 'ожидан'],
            ('m40', 'check'): ['max', 'назад', 'окна'],
        }
        for (mid, target), terms in needed.items():
            with self.subTest(mission=mid, target=target):
                text = self.linked_text(mid, target)
                for term in terms:
                    self.assertIn(term, text)

    def test_attention_and_sampling_examples_are_numerically_sound(self):
        # Recompute the independent demonstration and the different assessment.
        probs = [math.exp(v) / (1 + 3) for v in (0, math.log(3))]
        self.assertAlmostEqual(probs[0], .25)
        self.assertAlmostEqual(probs[1], .75)
        self.assertIn('[0.25, 0.75]', self.text('m22'))
        a = self.missions['m22']['activity']
        scores = [sum(q * k for q, k in zip(a['query'], key)) / math.sqrt(len(a['query'])) for key in a['keys']]
        self.assertEqual(scores.index(max(scores)), a['expectedIndex'])
        probabilities = [.6, .25, .1, .05]
        total = 0; count = 0
        for probability in probabilities:
            total += probability; count += 1
            if total >= .8: break
        self.assertEqual(count, 2)
        self.assertEqual(self.missions['m25']['check']['options'][self.missions['m25']['check']['answer']], 'Два')
        self.assertIn('[0.50,0.28,0.15,0.07]', self.text('m25'))
        self.assertLess(.50 + .28, .8)
        self.assertGreaterEqual(.50 + .28 + .15, .8)

    def test_dropout_experiment_is_taught_as_measurement_not_preset_success(self):
        text = self.text('m19')
        for concept in ['batchnorm', 'layernorm', 'dropout', 'p=0,0.2,0.8', 'начальных весах', 'no_grad', 'float', 'train', 'eval', 'не гарантировано']:
            self.assertIn(concept, text)
        self.assertIn('не обязана', text)  # Small masks need not zero exactly p*n.
        self.assertIn('не подменяет dropout', text)
        self.assertEqual(4 * 80 + 100 * 4, 720)
        self.assertIn('720', self.text('m34'))
        self.assertIn('не означает', self.text('m34'))

    def test_live_agent_and_offline_loop_have_distinct_honest_contracts(self):
        offline = self.text('m31'); live = self.text('m32')
        for term in ['test double', 'call_tool', 'position', 'budget', 'goal']:
            self.assertIn(term, offline)
        for term in ['localhost', 'http', 'от 1 до 4', 'json', 'observation', 'read_gate', 'open_gate', 'stop=true', 'не скачивает']:
            self.assertIn(term, live)
        self.assertIn('не удостоверяет реальные веса', live)
        self.assertIn('необязательный', live)

    def test_inventory_references_do_not_claim_unperformed_website_audit(self):
        sources = json.loads((ROOT / 'data/sources.json').read_text())
        indexed = {s['id']: s for s in sources['sources']}
        for sid in ['lensa-ml-reference', 'agent-mobile-reference', 'uva-pytorch-reference', 'hf-course-reference']:
            s = indexed[sid]
            self.assertEqual(s['verification'], 'inventory-reference')
            self.assertIsNone(s['checkedAt'])
            self.assertTrue(s['missions'])
            self.assertIn('не проверялся', s['readScope'])
            self.assertTrue(set(s['missions']).issubset(self.missions))


if __name__ == '__main__':
    unittest.main(verbosity=2)
