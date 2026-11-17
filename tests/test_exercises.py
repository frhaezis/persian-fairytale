"""Behaviour tests for the educational exercises (stdlib unittest)."""
import contextlib
import io
import importlib.util
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from exercises import EXERCISES, public_exercises, validate

HAS_TORCH = importlib.util.find_spec("torch") is not None


def execute(code):
    namespace = {"__name__": "__main__"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(code, "exercise.py", "exec"), namespace)
    return namespace


class ExerciseTests(unittest.TestCase):
    def test_public_metadata_excludes_reference_code(self):
        public = public_exercises()
        self.assertEqual(set(public), set(EXERCISES))
        self.assertGreaterEqual(len(public), 20)
        for item in public.values():
            self.assertNotIn("solution", item)
            self.assertTrue(item["starter"].strip())
        json.dumps(public, ensure_ascii=False)

    def test_notebook_has_matching_self_contained_exercises(self):
        path = pathlib.Path(__file__).resolve().parents[1] / "notebooks" / "practice.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        starters = {cell["metadata"]["exercise_id"]: "".join(cell["source"])
                    for cell in notebook["cells"] if cell["metadata"].get("role") == "starter"}
        self.assertEqual(set(starters), set(EXERCISES))
        for key, starter in starters.items():
            self.assertEqual(starter, EXERCISES[key]["starter"])
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), "notebook_cell", "exec")

    @unittest.skipUnless(HAS_TORCH, "PyTorch is required for notebook execution")
    def test_notebook_harness_runs_all_reference_implementations(self):
        path = pathlib.Path(__file__).resolve().parents[1] / "notebooks" / "practice.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        namespace = execute("".join(code_cells[0]["source"]) + "\n" + "".join(code_cells[1]["source"]))
        checker = namespace["validate"]
        for key, item in EXERCISES.items():
            with self.subTest(exercise=key):
                learner = execute(item["solution"])
                result = checker(key, learner, "transfer")
                self.assertTrue(result["passed"], result)

    def test_reference_implementations_practice_and_transfer(self):
        for key, item in EXERCISES.items():
            if item["requiresTorch"] and not HAS_TORCH:
                continue
            for variant in ("practice", "transfer"):
                with self.subTest(exercise=key, variant=variant):
                    namespace = execute(item["solution"])
                    result = validate(key, namespace, variant)
                    self.assertTrue(result["passed"], result)
                    self.assertTrue(all(r["passed"] for r in result["results"]))
                    json.dumps(result, ensure_ascii=False)

    def test_starters_do_not_award_unearned_completion(self):
        for key, item in EXERCISES.items():
            if item["requiresTorch"] and not HAS_TORCH:
                continue
            with self.subTest(exercise=key):
                try:
                    namespace = execute(item["starter"])
                except Exception:
                    # An unfinished starter may fail at its demo call. It cannot pass.
                    continue
                self.assertFalse(validate(key, namespace)["passed"])

    def test_unknown_exercise_and_missing_function_are_explained(self):
        self.assertFalse(validate("does_not_exist", {})["passed"])
        result = validate("metrics", {})
        self.assertFalse(result["passed"])
        self.assertIn("classification_metrics", result["feedback"])

    def test_metrics_detect_precision_recall_confusion(self):
        namespace = execute(EXERCISES["metrics"]["solution"])
        correct = namespace["classification_metrics"]
        def confused(truth, pred):
            result = correct(truth, pred)
            result["precision"], result["recall"] = result["recall"], result["precision"]
            return result
        self.assertFalse(validate("metrics", {"classification_metrics": confused})["passed"])
        self.assertFalse(validate("metrics", {"classification_metrics": confused}, "transfer")["passed"])

    def test_agent_budget_and_actual_tool_results(self):
        def teleport(tool, start, target, budget):
            return {"position": target, "calls": 0, "reason": "goal"}
        self.assertFalse(validate("agent_loop", {"navigate": teleport})["passed"])
        def ignores_result(tool, start, target, budget):
            pos, calls = start, 0
            while pos != target and calls < budget:
                direction = 1 if target > pos else -1
                tool("step", {"position": pos, "delta": direction})
                pos += direction
                calls += 1
            return {"position": pos, "calls": calls, "reason": "goal" if pos == target else "budget"}
        self.assertFalse(validate("agent_loop", {"navigate": ignores_result})["passed"])

    def test_algorithm_boundary_mistakes(self):
        def wrong_pair(nums, target):
            for i, value in enumerate(nums):
                if value * 2 == target:
                    return [i, i]
            return []
        self.assertFalse(validate("two_sum", {"two_sum": wrong_pair})["passed"])
        def counts_only(value):
            return all(value.count(a) == value.count(b) for a,b in [("(",")"),("[","]"),("{","}")])
        self.assertFalse(validate("brackets", {"balanced": counts_only})["passed"])

    @unittest.skipUnless(HAS_TORCH, "PyTorch is required for actual tensor checks")
    def test_optimizer_detects_missing_zero_grad(self):
        import torch
        def wrong(model, x, y, optimizer):
            model.train()
            loss = torch.nn.functional.mse_loss(model(x), y)
            loss.backward()
            optimizer.step()
            return loss.item()
        self.assertFalse(validate("optimizer", {"train_step": wrong})["passed"])

    @unittest.skipUnless(HAS_TORCH, "PyTorch is required for actual tensor checks")
    def test_eval_and_no_grad_are_independent(self):
        import torch
        def only_eval(model, x):
            model.eval()
            return model(x)
        def only_no_grad(model, x):
            with torch.no_grad():
                return model(x)
        self.assertFalse(validate("modes", {"predict": only_eval})["passed"])
        self.assertFalse(validate("modes", {"predict": only_no_grad})["passed"])

    @unittest.skipUnless(HAS_TORCH, "PyTorch is required for actual tensor checks")
    def test_softmax_before_cross_entropy_is_rejected(self):
        import torch
        def wrong(kind, predictions, targets):
            if kind == "regression":
                return torch.nn.functional.mse_loss(predictions, targets)
            if kind == "classification":
                return torch.nn.functional.cross_entropy(predictions.softmax(-1), targets)
            raise ValueError("unknown")
        self.assertFalse(validate("losses", {"loss_for": wrong})["passed"])

    @unittest.skipUnless(HAS_TORCH, "PyTorch is required for actual tensor checks")
    def test_training_validation_leakage_is_rejected(self):
        namespace = execute(EXERCISES["training"]["solution"])
        correct = namespace["fit_line"]
        def leaks(x, y, xv, yv):
            import torch
            return correct(torch.cat([x,xv]), torch.cat([y,yv]), xv, yv)
        self.assertFalse(validate("training", {"fit_line": leaks})["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
