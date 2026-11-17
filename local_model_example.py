"""Optional local-only Transformers adapter example, never started by the game.

Usage: python local_model_example.py "C:\\models\\qwen" --max-new-tokens 48
Requires a compatible Hugging Face model directory and separately installed
transformers, accelerate and torch. No weight download or remote model code.
This example does not create an HTTP API. Use an actual inference server to
connect the game's optional OpenAI-compatible API adapter.
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Необязательный локальный пример Transformers; CPU, без скачивания весов")
    parser.add_argument("path", type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument("--prompt", default="Explain the difference between a model and an agent in two sentences.")
    args = parser.parse_args()
    path = args.path.expanduser().resolve()
    if not path.is_dir() or not (path / "config.json").is_file():
        parser.error("Нужна папка формата Transformers с config.json. GGUF требует другого runtime.")
    config = json.loads((path / "config.json").read_text(encoding="utf-8"))
    print("Архитектура из config.json:", config.get("architectures", config.get("model_type", "не указана")))
    print("Загрузка только локальных файлов. 4B-модель на CPU может потребовать много RAM и работать медленно.")
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        parser.error("Необязательная зависимость отсутствует: %s. Основная игра от этого примера не зависит." % exc)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(str(path), local_files_only=True,
                                                trust_remote_code=False, torch_dtype=torch.float32,
                                                low_cpu_mem_usage=True)
    model.eval()
    messages = [{"role": "user", "content": args.prompt}]
    if getattr(tokenizer, "chat_template", None):
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        prompt = args.prompt
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        result = model.generate(**inputs, max_new_tokens=max(1, min(128, args.max_new_tokens)),
                                do_sample=False, pad_token_id=tokenizer.eos_token_id)
    print(tokenizer.decode(result[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True))


if __name__ == "__main__":
    main()
