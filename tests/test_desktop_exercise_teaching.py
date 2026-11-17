"""Content contracts plus executable causal checks for V2 preparation."""
import contextlib
import io
import json
import math
from pathlib import Path
import sys
import unittest

import torch
from torch import nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from exercises import EXERCISES, public_exercises, validate


def solution(key):
    namespace = {}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(EXERCISES[key]["solution"], namespace)
    return namespace


class ExerciseTeachingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teaching = json.loads((ROOT/"data/exercise_teaching.json").read_text())
        torch.set_num_threads(1)

    def test_every_actual_exercise_exposes_its_own_contract_and_preparation(self):
        public = public_exercises()
        self.assertEqual(set(self.teaching), set(EXERCISES))
        for key, exercise in EXERCISES.items():
            with self.subTest(key=key):
                lesson = public[key]["teaching"]
                self.assertEqual(lesson["taskBridge"], exercise["description"])
                self.assertTrue(lesson["prerequisites"])
                self.assertGreaterEqual(len(lesson["steps"]), 4)
                self.assertTrue(lesson["workedExample"]["steps"])
                self.assertTrue(lesson["pitfalls"])
                self.assertTrue(lesson["interview"])
                for item in lesson["prerequisites"]:
                    self.assertTrue(item["explanation"])

    def test_all_twenty_worked_examples_are_executable(self):
        for key, lesson in self.teaching.items():
            with self.subTest(key=key), contextlib.redirect_stdout(io.StringIO()):
                exec(compile(lesson["workedExample"]["code"], key+"_worked.py", "exec"),
                     {"torch":torch,"nn":nn,"F":F,"math":math})

    def test_controlled_experiment_records_six_observed_curves(self):
        namespace = solution("normalization")
        result = validate("normalization", namespace)
        self.assertTrue(result["passed"], result)
        artifact = result["artifact"]
        self.assertEqual(len(artifact["series"]), 6)
        self.assertEqual(artifact["parameters"]["probabilities"], [0,.2,.8])
        for series in artifact["series"]:
            self.assertEqual(series["steps"], list(range(41)))
            self.assertEqual(len(series["values"]), 41)
            self.assertTrue(all(math.isfinite(x) for x in series["values"]))
            self.assertNotEqual(series["values"][0], series["values"][-1])
        self.assertEqual(artifact["series"][0]["values"][0], artifact["series"][2]["values"][0])
        self.assertEqual(artifact["series"][2]["values"][0], artifact["series"][4]["values"][0])
        repeated = validate("normalization", solution("normalization"))["artifact"]
        self.assertEqual(artifact, repeated)
        transferred = validate("normalization", solution("normalization"), "transfer")["artifact"]
        self.assertNotEqual(artifact["series"], transferred["series"])

    def test_chart_uses_learner_model_instead_of_fixed_reference_curves(self):
        baseline = solution("normalization")
        baseline_result = validate("normalization", baseline)
        altered = solution("normalization")
        factory = altered["build_dropout_model"]
        def different_initial_weights(p):
            model = factory(p)
            with torch.no_grad():
                for parameter in model.parameters():
                    parameter.mul_(.5)
            return model
        altered["build_dropout_model"] = different_initial_weights
        altered_result = validate("normalization", altered)
        self.assertTrue(altered_result["passed"], altered_result)
        self.assertNotEqual(baseline_result["artifact"]["series"], altered_result["artifact"]["series"])

    def test_no_chart_for_missing_dropout_or_incorrect_evaluation(self):
        namespace = solution("normalization")
        namespace["build_dropout_model"] = lambda p: nn.Sequential(nn.Linear(2,16), nn.ReLU(), nn.Identity(), nn.Linear(16,1))
        result = validate("normalization", namespace)
        self.assertFalse(result["passed"])
        self.assertNotIn("artifact", result)
        for mistake in ("eval_only", "no_grad_only", "constant"):
            namespace = solution("normalization")
            def incorrect(model,x,y):
                if mistake == "constant":
                    return 1.0
                if mistake == "eval_only":
                    model.eval()
                    return F.mse_loss(model(x),y).item()
                with torch.no_grad():
                    return F.mse_loss(model(x),y).item()
            namespace["evaluate_mse"] = incorrect
            result = validate("normalization", namespace)
            self.assertFalse(result["passed"], mistake)
            self.assertNotIn("artifact", result)


if __name__ == "__main__":
    unittest.main()
