"""Build the optional, self-contained notebook from the same lessons and checks."""
from pathlib import Path
import inspect
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import exercises


def cell(kind, source, metadata=None):
    result = {"cell_type": kind, "metadata": metadata or {}, "source": source.splitlines(True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def teaching_markdown(lesson):
    parts = [lesson["goal"], "### Что понадобится"]
    for item in lesson["prerequisites"]:
        parts += ["**" + item["name"] + "**", item["explanation"]]
        if item.get("example"):
            parts += ["```text\n" + item["example"] + "\n```"]
    for index, item in enumerate(lesson["steps"], 1):
        parts += [f"### {index}. {item['title']}", item["text"]]
        if item.get("code"):
            parts += ["```python\n" + item["code"] + "\n```"]
        if item.get("example"):
            parts += [item["example"]]
    example = lesson["workedExample"]
    parts += ["### " + example["title"], "\n".join(f"{i}. {s}" for i,s in enumerate(example["steps"],1))]
    if example.get("code"):
        parts += ["```python\n" + example["code"] + "\n```"]
    parts += ["### Самостоятельная задача", lesson["taskBridge"]]
    return "\n\n".join(parts)


def main():
    tutorials=json.loads((ROOT/"data/exercise_teaching.json").read_text(encoding="utf-8"))
    cells = [cell("markdown", "# persian fairytale. V2 — запасная мастерская Python / PyTorch\n\n"
                  "Те же объяснения, упражнения и настоящие проверки, что в игре. Можно открыть в локальном Jupyter или Google Colab. "
                  "Внешняя среда может потребовать установку PyTorch. Данные синтетические; прогресс notebook не переносится в игру автоматически. "
                  "Сначала разберите объяснение, затем измените starter и запустите проверку. Эталон раскрывается отдельно."),
             cell("code", "# При отсутствии PyTorch раскомментируйте: установка требует интернета.\n# %pip install torch numpy\n"
                          "import sys, math, json\nimport torch\ntorch.set_num_threads(1)\n"
                          "torch.manual_seed(7)\nprint('Python', sys.version.split()[0], 'PyTorch', torch.__version__, 'CPU')\n")]
    metadata = {key: {"requiresTorch": v["requiresTorch"], "hint": v["hint"]} for key,v in exercises.EXERCISES.items()}
    harness = "# Самостоятельные проверочные случаи и построение графиков из настоящих вычислений.\nEXERCISES = " + repr(metadata) + "\n\n"
    harness += inspect.getsource(exercises._dropout_experiment) + "\n\n" + inspect.getsource(exercises.validate)
    cells.append(cell("code", harness, {"cellView":"form", "jupyter":{"source_hidden":True}}))
    for number, (key, exercise) in enumerate(exercises.EXERCISES.items(),1):
        cells.append(cell("markdown", f"## {number}. {exercise['title']}\n\n" + teaching_markdown(tutorials[key])))
        cells.append(cell("code", exercise["starter"], {"exercise_id":key,"role":"starter"}))
        check = f"result = validate({key!r}, globals(), variant='practice')\n"
        check += "for case in result['results']:\n    print(('✓ ' if case['passed'] else '✗ ') + case['name'] + ': ' + case['detail'])\nprint(result['feedback'])\n"
        check += "if result.get('artifact'):\n    for observation in result['artifact'].get('observations', []):\n        print(observation)\n"
        check += "# После самостоятельного объяснения замените practice на transfer для других входов.\n"
        cells.append(cell("code", check, {"exercise_id":key,"role":"validation"}))
        lesson=tutorials[key]
        review="### Проверка причин и ошибок\n\n"+"\n\n".join("**"+p["symptom"]+"** — "+p["explanation"] for p in lesson["pitfalls"])
        review+="\n\n**Объяснение для собеседования:** "+lesson["interview"]
        review+="\n\n<details><summary>Эталон — после самостоятельной попытки</summary>\n\n```python\n"+exercise["solution"]+"\n```\n\n</details>"
        cells.append(cell("markdown", review, {"exercise_id":key,"role":"reference"}))
    notebook={"nbformat":4,"nbformat_minor":5,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python"}},"cells":cells}
    (ROOT/"notebooks/practice.ipynb").write_text(json.dumps(notebook,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
    print("Notebook:", len(cells), "cells,", len(exercises.EXERCISES), "complete tutorials")


if __name__ == "__main__":
    main()
