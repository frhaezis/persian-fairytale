"""Structural and mathematical checks of the complete authored route.

These checks establish coverage, references, solvability and budget arithmetic;
they do not establish human learning effectiveness or observed play duration.
"""
import json
import math
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from exercises import EXERCISES


def read_curriculum():
    return json.loads((ROOT / "data" / "curriculum.json").read_text(encoding="utf-8"))


def legal_thresholds(activity):
    positives, negatives = activity["positive"], activity["negative"]
    return [i / 100 for i in range(101)
            if sum(score >= i / 100 for score in positives) / len(positives) >= activity["targetRecall"]
            and sum(score >= i / 100 for score in negatives) <= activity["maxFP"]]


class CurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = read_curriculum()
        cls.missions = cls.data["missions"]
        source_data = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
        cls.sources = {source["id"]: source for source in source_data["sources"]}

    def test_complete_four_act_route_and_budget(self):
        self.assertEqual([m["id"] for m in self.missions], [f"m{i:02}" for i in range(1, 41)])
        self.assertEqual([a["id"] for a in self.data["acts"]], [1, 2, 3, 4])
        self.assertEqual(sum(m["minutes"] for m in self.missions), 1200)
        for act in self.data["acts"]:
            self.assertEqual(sum(m["act"] == act["id"] for m in self.missions), 10)
            for field in ["title", "place", "intro", "outro"]:
                self.assertTrue(act[field].strip())
        torch_minutes = sum(m["minutes"] for m in self.missions if m["id"] in {f"m{i:02}" for i in range(11, 20)})
        self.assertEqual(torch_minutes, 240)

    def test_each_mission_is_authored_referenced_and_reachable(self):
        previous = set()
        rewards = []
        for index, mission in enumerate(self.missions):
            with self.subTest(mission=mission["id"]):
                self.assertEqual(mission["act"], index // 10 + 1)
                self.assertTrue(set(mission["prerequisites"]).issubset(previous))
                self.assertNotIn(mission["id"], mission["prerequisites"])
                self.assertIn(mission["npc"], {"Лейла", "Сафар", "Нур"})
                for field in ["title", "objective", "workedExample", "hint", "remedial"]:
                    self.assertGreater(len(mission[field].strip()), 3)
                self.assertIn(mission["station"], ["gate", "archive", "workshop", "observatory", "garden"])
                self.assertTrue(mission["story"])
                self.assertTrue(all(line["speaker"].strip() and line["text"].strip() for line in mission["story"]))
                self.assertTrue(mission["lesson"])
                for lesson in mission["lesson"]:
                    self.assertGreaterEqual(len(lesson.split()), 30, "Explain one meaningful idea, not a title")
                    self.assertLessEqual(len(lesson.split()), 140, "Avoid an unbroken lecture panel")
                authored = json.dumps(mission, ensure_ascii=False)
                self.assertIsNone(re.search(r"\b(?:TODO|TBD|lorem ipsum)\b|ЗДЕСЬ БУДЕТ", authored, re.I))
                self.assertTrue(mission["topics"])
                for topic in mission["topics"]:
                    self.assertIn(topic["depth"], ["apply", "explain", "recognize"])
                    self.assertGreater(len(topic["example"].strip()), 12)
                    self.assertGreater(len(topic["question"].strip()), 10)
                    source = topic["source"]
                    self.assertTrue(source in self.sources or source.startswith("https://"), source)
                reflection = mission["reflection"]
                self.assertGreater(len(reflection["prompt"]), 10)
                self.assertGreater(len(reflection["model"]), 20)
                self.assertGreaterEqual(len(reflection["checklist"]), 2)
                self.assertTrue(mission["practicePlan"])
                self.assertEqual(sum(step["minutes"] for step in mission["practicePlan"]), mission["minutes"])
                self.assertTrue(all(step["minutes"] > 0 and step["task"].strip() for step in mission["practicePlan"]))
                self.assertTrue(mission["reward"]["item"].strip())
                self.assertTrue(mission["reward"]["text"].strip())
                rewards.append(mission["reward"]["item"])
                previous.add(mission["id"])
        self.assertEqual(len(set(rewards)), len(rewards), "Authored rewards should be identifiable")

    def test_checks_are_valid_and_transfer_cases_are_different(self):
        for mission in self.missions:
            with self.subTest(mission=mission["id"]):
                for name in ["check", "transfer"]:
                    check = mission[name]
                    self.assertGreater(len(check["question"]), 10)
                    self.assertGreaterEqual(len(check["options"]), 2)
                    self.assertEqual(len(check["options"]), len(set(check["options"])))
                    self.assertIsInstance(check["answer"], int)
                    self.assertGreaterEqual(check["answer"], 0)
                    self.assertLess(check["answer"], len(check["options"]))
                    self.assertGreater(len(check["explanation"]), 15)
                self.assertNotEqual(mission["check"]["question"], mission["transfer"]["question"])

    def test_all_activity_types_are_satisfiable_and_well_formed(self):
        seen = set()
        for mission in self.missions:
            activity = mission["activity"]
            kind = activity["type"]
            seen.add(kind)
            with self.subTest(mission=mission["id"], kind=kind):
                self.assertIn(kind, ["code", "threshold", "split", "compare", "attention", "retrieval", "agent"])
                if kind == "code":
                    self.assertIn(activity["exerciseId"], EXERCISES)
                elif kind == "threshold":
                    self.assertTrue(activity["positive"] and activity["negative"])
                    self.assertTrue(all(isinstance(x, (int, float)) and 0 <= x <= 1 for x in activity["positive"] + activity["negative"]))
                    self.assertGreaterEqual(activity["targetRecall"], 0)
                    self.assertLessEqual(activity["targetRecall"], 1)
                    self.assertTrue(legal_thresholds(activity), "No threshold reachable by the 0.01 UI slider satisfies the mission")
                elif kind == "split":
                    records = activity["records"]
                    self.assertGreaterEqual(len(records), 3)
                    self.assertEqual(len({r["id"] for r in records}), len(records))
                    self.assertTrue(all(r["group"] in ["train", "validation", "test"] and r["label"].strip() for r in records))
                elif kind == "compare":
                    categories, cards = activity["categories"], activity["cards"]
                    self.assertGreaterEqual(len(categories), 2)
                    self.assertEqual(len(categories), len(set(categories)))
                    self.assertGreaterEqual(len(cards), 2)
                    self.assertTrue(all(card["category"] in categories and card["label"].strip() for card in cards))
                elif kind == "attention":
                    query, keys, values = activity["query"], activity["keys"], activity["values"]
                    self.assertTrue(query and keys and values)
                    self.assertEqual(len(keys), len(values))
                    self.assertTrue(all(len(key) == len(query) for key in keys))
                    self.assertTrue(all(len(value) == len(values[0]) for value in values))
                    self.assertTrue(all(math.isfinite(x) for row in [query] + keys + values for x in row))
                    scores = [sum(x * y for x, y in zip(query, key)) for key in keys]
                    self.assertEqual(activity["expectedIndex"], scores.index(max(scores)))
                    self.assertEqual(scores.count(max(scores)), 1, "Largest attention weight must have a unique answer")
                elif kind == "retrieval":
                    docs = activity["documents"]
                    ids = {doc["id"] for doc in docs}
                    self.assertEqual(len(ids), len(docs))
                    self.assertTrue(activity["required"])
                    self.assertTrue(set(activity["required"]).issubset(ids))
                    self.assertEqual(set(activity["required"]), {doc["id"] for doc in docs if doc["relevant"]})
                    self.assertTrue(all(doc["title"].strip() and doc["text"].strip() for doc in docs))
                elif kind == "agent":
                    self.assertGreaterEqual(len(activity["steps"]), 4)
                    self.assertEqual(len(activity["steps"]), len(set(activity["steps"])))
                    self.assertTrue(activity["goal"].strip())
        self.assertEqual(seen, {"code", "threshold", "split", "compare", "attention", "retrieval", "agent"})

    def test_every_employer_topic_is_named_in_the_topic_map(self):
        names = "\n".join(topic["name"] for mission in self.missions for topic in mission["topics"]).lower()
        names = names.replace("‑", "-").replace("–", "-").replace("—", "-")
        patterns = {
            "supervised": r"\bsupervised", "unsupervised": r"\bunsupervised", "self-supervised": r"self-supervised",
            "linear regression": r"linear regression", "logistic regression": r"logistic regression",
            "L1": r"\bl1\b", "L2": r"\bl2\b", "Decision Tree": r"decision tree", "Random Forest": r"random forest",
            "Gradient Boosting": r"gradient boosting", "XGBoost": r"xgboost", "LightGBM": r"lightgbm", "CatBoost": r"catboost",
            "SVM": r"\bsvm\b", "KNN": r"\bknn\b", "Naive Bayes": r"naive bayes", "K-Means": r"k-means", "DBSCAN": r"dbscan", "PCA": r"\bpca\b",
            "bias-variance": r"bias.variance", "overfitting": r"overfitting", "underfitting": r"underfitting",
            "cross-validation": r"cross.validation", "hyperparameter tuning": r"hyperparameter tuning",
            "data leakage": r"data leakage", "feature engineering": r"feature engineering", "missing values": r"missing values",
            "Precision": r"precision", "Recall": r"recall", "F1": r"\bf1\b", "Accuracy": r"accuracy", "confusion matrix": r"confusion matrix",
            "backpropagation": r"backpropagation", "computational graph": r"computational graph", "cross-entropy": r"cross.entropy",
            "contrastive loss": r"contrastive loss", "MSE": r"\bmse\b", "BatchNorm": r"batchnorm", "LayerNorm": r"layernorm", "Dropout": r"dropout",
            "BPE": r"\bbpe\b", "vocabulary": r"vocabulary", "context window": r"context window", "self-attention": r"self.attention",
            "multi-head attention": r"multi.head attention", "Q": r"\bq\b", "K": r"\bk\b", "V": r"\bv\b", "scaled dot-product attention": r"scaled dot.product attention",
            "encoder-only": r"encoder.only", "decoder-only": r"decoder.only", "encoder-decoder": r"encoder.decoder",
            "pretraining": r"pretraining", "instruction tuning": r"instruction tuning", "SFT": r"\bsft\b", "RLHF": r"\brlhf\b", "DPO": r"\bdpo\b",
            "temperature": r"temperature", "top-p": r"top.p", "top-k": r"top.k", "sampling": r"sampling", "KV cache": r"kv cache", "prefill": r"prefill", "decode": r"decode",
            "hallucinations": r"hallucination", "prompt engineering": r"prompt engineering", "structured outputs": r"structured output", "function calling": r"function calling",
            "RAG": r"\brag\b|retrieval.augmented generation", "agent": r"\bagent\b", "chatbot": r"chatbot", "deterministic workflow": r"deterministic workflow",
            "tool calling": r"tool calling", "tool schemas": r"tool schema", "single-agent": r"single.agent", "multi-agent": r"multi.agent", "MCP": r"\bmcp\b",
            "full fine-tuning": r"full fine.tuning", "PEFT": r"\bpeft\b", "LoRA": r"\blora\b", "QLoRA": r"\bqlora\b",
            "SFT dataset preparation": r"sft dataset preparation", "chat templates": r"chat template", "INT8": r"int8", "INT4": r"int4", "GGUF": r"gguf",
            "model distillation": r"model.*distillation", "knowledge distillation": r"knowledge distillation",
            "LLM-as-a-judge": r"llm.as.a.judge", "calibration": r"calibration", "vLLM": r"vllm", "continuous batching": r"continuous batching", "caching": r"caching",
        }
        missing = [name for name, pattern in patterns.items() if not re.search(pattern, names)]
        self.assertEqual(missing, [], "Every employer subtopic needs an explicit topic-map entry, example and question")

    def test_four_algorithm_rehearsals_have_timers(self):
        by_id = {m["id"]: m for m in self.missions}
        for mission_id in ["m10", "m20", "m38", "m40"]:
            with self.subTest(mission=mission_id):
                self.assertTrue(by_id[mission_id]["activity"].get("timed"), "15-minute rehearsal must expose an actual timer")


if __name__ == "__main__":
    unittest.main(verbosity=2)
