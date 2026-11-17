# Источники persian fairytale. V2

Дата проверки: 2026-11-16. Реестр для приложения: `data/sources.json`. Поле `topic.source` ссылается на `id` этого реестра.

Прочитаны указанные разделы первоисточников, а не все страницы целиком. Тексты уроков и художественный мир оригинальные. Внешние ссылки необязательны для прохождения; игра не загружает эти страницы автоматически.

## `python-data-structures` — [Data Structures](https://docs.python.org/3/tutorial/datastructures.html)

Python. Проверено: 2026-11-16. Прочитано: Lists as Stacks; Lists as Queues; Dictionaries; Looping Techniques.

Списки, стек, очередь, множества, словарь и обход коллекций.

Граница применения: В учебных алгоритмах отдельно учитываются предварительные условия и сложность; наличие словаря не гарантирует worst-case O(1).

- [bisect — Array bisection algorithm](https://docs.python.org/3/library/bisect.html) — Introduction; bisect_left partition invariant. Проверено: 2026-11-16.

## `pandas-basics` — [How do I select a subset of a DataFrame?](https://pandas.pydata.org/docs/getting_started/intro_tutorials/03_subset_data.html)

pandas. Проверено: 2026-11-16. Прочитано: Specific columns; filtering rows.

DataFrame/Series; выбор колонок; boolean filtering; форма таблицы.

Граница применения: Данные Titanic из источника не включены в игру; используются собственные маленькие таблицы.

## `numpy-basics` — [NumPy: the absolute basics for beginners](https://numpy.org/doc/stable/user/absolute_beginners.html)

NumPy. Проверено: 2026-11-16. Прочитано: What is an array?; Array fundamentals; Array attributes; Basic array operations; Broadcasting.

Массивы, shape, axis, dtype, срезы, elementwise operations и broadcasting.

Граница применения: Elementwise multiplication не совпадает с матричным произведением; срез NumPy часто является view.

## `sklearn-pitfalls` — [Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html)

scikit-learn. Проверено: 2026-11-16. Прочитано: Inconsistent preprocessing; Data leakage; How to avoid data leakage.

Разделение данных до обучения преобразований; fit только на train; transform на остальных данных; Pipeline против утечки.

Граница применения: Pipeline помогает только при корректном разбиении; временная и групповая утечки требуют подходящей схемы split.

- [Imputation of missing values](https://scikit-learn.org/stable/modules/impute.html) — Introduction; SimpleImputer. Проверено: 2026-11-16.

## `sklearn-metrics` — [Metrics and scoring: quantifying the quality of predictions](https://scikit-learn.org/stable/modules/model_evaluation.html)

scikit-learn. Проверено: 2026-11-16. Прочитано: Which scoring function should I use?; Precision, recall and F-measures; Binary classification.

Precision, recall, F1, confusion matrix; выбор метрики в соответствии с ценой ошибки.

Граница применения: Порог меняет рабочую точку; высокая accuracy сама по себе не доказывает качество на редком классе.

## `sklearn-supervised` — [Supervised learning](https://scikit-learn.org/stable/supervised_learning.html)

scikit-learn. Проверено: 2026-11-16. Прочитано: Обзор главы и релевантные введения связанных страниц.

Семейства supervised-моделей; линейная регрессия, SVM, деревья, ансамбли.

Граница применения: Обзор не означает, что один алгоритм подходит всем задачам. XGBoost, LightGBM и CatBoost все поддерживают разные настройки; сходство или преимущество проверяется на своей задаче, а не по бренду.

- [Linear Models](https://scikit-learn.org/stable/modules/linear_model.html) — Ordinary Least Squares; Ridge; Lasso; Logistic regression; binary formula. Проверено: 2026-11-16.
- [Support Vector Machines](https://scikit-learn.org/stable/modules/svm.html) — Introduction; Classification. Проверено: 2026-11-16.
- [Decision Trees](https://scikit-learn.org/stable/modules/tree.html) — Introduction; advantages and limitations. Проверено: 2026-11-16.
- [Ensembles](https://scikit-learn.org/stable/modules/ensemble.html) — Introduction; Gradient-boosted trees; Random Forests. Проверено: 2026-11-16.
- [Introduction to Boosted Trees — XGBoost](https://xgboost.readthedocs.io/en/stable/tutorials/model.html) — Introduction; training loss plus regularization. Проверено: 2026-11-16.
- [Features — LightGBM](https://lightgbm.readthedocs.io/en/stable/Features.html) — Histogram algorithm; leaf-wise growth; categorical features. Проверено: 2026-11-16.
- [How training is performed — CatBoost](https://catboost.ai/docs/en/concepts/algorithm-main-stages) — Overview; consecutive trees; categorical feature stage. Проверено: 2026-11-16.
- [Nearest Neighbors](https://scikit-learn.org/stable/modules/neighbors.html) — Introduction; neighbors-based classification and regression. Проверено: 2026-11-16.
- [Naive Bayes](https://scikit-learn.org/stable/modules/naive_bayes.html) — Introduction; conditional independence assumption; probability caveat. Проверено: 2026-11-16.

- [CatBoost: unbiased boosting with categorical features](https://arxiv.org/abs/1706.09516) — Abstract: ordered boosting и обработка категорий. Проверено: 2026-11-16.
- [Categorical features — CatBoost](https://catboost.ai/docs/en/features/categorical-features) — categorical support и условия внутренних преобразований. Проверено: 2026-11-16.

## `sklearn-unsupervised` — [Unsupervised learning](https://scikit-learn.org/stable/unsupervised_learning.html)

scikit-learn. Проверено: 2026-11-16. Прочитано: Обзор главы; Clustering introduction, K-means and DBSCAN.

Различие кластеризации и задачи с целевой меткой; K-means, DBSCAN, PCA как семейства.

Граница применения: Кластеры не становятся истинными классами автоматически; масштаб признаков и расстояние влияют на результат.

- [Clustering](https://scikit-learn.org/stable/modules/clustering.html) — Overview; K-means; DBSCAN. Проверено: 2026-11-16.
- [Principal component analysis](https://scikit-learn.org/stable/modules/decomposition.html) — Exact PCA; centering without scaling. Проверено: 2026-11-16.

## `sklearn-model-selection` — [Cross-validation: evaluating estimator performance](https://scikit-learn.org/stable/modules/cross_validation.html)

scikit-learn. Проверено: 2026-11-16. Прочитано: Введение, validation holdout и описание k-fold.

Роли train, validation и test; k-fold CV; опасность настройки модели по test.

Граница применения: Обычная случайная CV не подходит автоматически временным и связанным наблюдениям.

## `pytorch-quickstart` — [Quickstart](https://docs.pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html)

PyTorch. Проверено: 2026-11-16. Прочитано: Optimizing Model Parameters; training loop; test loop.

nn.Module, DataLoader, loss, backward, optimizer.step, zero_grad; train/eval и no_grad.

Граница применения: Учебные примеры игры используют маленькие синтетические данные и CPU; они не воспроизводят benchmark из документации.

## `pytorch-autograd` — [Automatic Differentiation with torch.autograd](https://docs.pytorch.org/tutorials/beginner/basics/autogradqs_tutorial.html)

PyTorch. Проверено: 2026-11-16. Прочитано: Computing Gradients; Disabling Gradient Tracking; More on Computational Graphs.

requires_grad, вычислительный граф, backward, .grad, накопление градиентов, no_grad и detach.

Граница применения: backward вычисляет градиенты; сами веса обновляет optimizer. Градиенты нелистовых узлов можно сохранять специально, это не поведение по умолчанию.

## `pytorch-losses` — [CrossEntropyLoss](https://docs.pytorch.org/docs/2.15/generated/torch.nn.CrossEntropyLoss.html)

PyTorch. Проверено: 2026-11-16. Прочитано: Описание входов и targets; формулы; note on LogSoftmax.

CrossEntropyLoss принимает logits; варианты целевых индексов и распределений; связь с LogSoftmax и NLLLoss.

Граница применения: Для обычной многоклассовой классификации перед CrossEntropyLoss не нужно отдельно применять softmax к входу. Contrastive loss — семейство функций, а не одно название API; в упражнениях явно задано соглашение о метках пары.

- [MSELoss](https://docs.pytorch.org/docs/2.15/generated/torch.nn.MSELoss.html) — Formula; reduction; tensor shapes. Проверено: 2026-11-16.
- [CosineEmbeddingLoss](https://docs.pytorch.org/docs/2.15/generated/torch.nn.CosineEmbeddingLoss.html) — Pair labels; cosine and margin loss formula. Проверено: 2026-11-16.
- [A Simple Framework for Contrastive Learning of Visual Representations](https://arxiv.org/abs/2002.05709) — Abstract. Проверено: 2026-11-16.

## `pytorch-normalization` — [LayerNorm](https://docs.pytorch.org/docs/2.15/generated/torch.nn.LayerNorm.html)

PyTorch. Проверено: 2026-11-16. Прочитано: Formula, normalized_shape, statistics in train/eval; BatchNorm1d formula and running statistics.

LayerNorm нормализует последние normalized_shape измерения; сравнение с BatchNorm и роль train/eval.

Граница применения: BatchNorm обычно использует running statistics в eval; при track_running_stats=False поведение другое.

- [BatchNorm1d](https://docs.pytorch.org/docs/2.15/generated/torch.nn.BatchNorm1d.html) — Formula; running statistics; track_running_stats. Проверено: 2026-11-16.
- [Dropout](https://docs.pytorch.org/docs/2.15/generated/torch.nn.Dropout.html) — Training zeroing probability; scaling; evaluation identity. Проверено: 2026-11-16.

## `transformer-paper` — [Attention Is All You Need](https://arxiv.org/html/1706.03762v7)

Vaswani et al.. Проверено: 2026-11-16. Прочитано: Abstract; section 3.2, especially 3.2.1 and 3.2.2.

Scaled dot-product attention, Q/K/V, масштаб 1/sqrt(d_k), multi-head attention.

Граница применения: Метафора внимания в игре не утверждает наличие человеческого сознания; наиболее высокий вес внимания не является доказательством причинности.

## `hf-tokenizers` — [Tokenization algorithms](https://huggingface.co/docs/transformers/main/en/tokenizer_summary)

Hugging Face. Проверено: 2026-11-16. Прочитано: Introduction; Byte pair encoding.

Токены и subword-разбиение; BPE, WordPiece и Unigram; словарь и зависимость разбиения от tokenizer.

Граница применения: Токен не равен слову; приведённое разбиение является учебным и зависит от конкретного словаря. Страница main может меняться.

## `hf-architectures` — [Transformer Architectures](https://huggingface.co/learn/llm-course/chapter1/6)

Hugging Face. Проверено: 2026-11-16. Прочитано: Introduction; Encoder models; Decoder models.

Различие encoder-only, decoder-only и encoder-decoder; типичные задачи и causal attention.

Граница применения: Это распространённые архитектурные семейства, а не исчерпывающая классификация всех моделей.

## `hf-kv-cache` — [How caching works](https://huggingface.co/docs/transformers/cache_explanation)

Hugging Face. Проверено: 2026-11-16. Прочитано: Introduction; Attention matrices.

Повторное использование K/V прошлых токенов во время autoregressive inference; цена памяти.

Граница применения: KV cache не база знаний и не долгосрочная память агента; его применение и размер зависят от архитектуры.

## `hf-generation` — [Generation strategies](https://huggingface.co/docs/transformers/generation_strategies)

Hugging Face. Проверено: 2026-11-16. Прочитано: Basic decoding methods: Greedy search, Sampling, Beam search.

Greedy decoding, sampling и beam search; generate и max_new_tokens. Temperature меняет распределение logits, top-k ограничивает число кандидатов, top-p ограничивает накопленную вероятность.

Граница применения: Случайность декодирования не измеряет истинность; remote custom generation из документации игра не загружает.

- [GenerationConfig](https://huggingface.co/docs/transformers/main_classes/text_generation) — Output length; generation strategy; temperature, top_k, top_p. Проверено: 2026-11-16.

Дополнительно прочитаны:

- [Prompt engineering](https://huggingface.co/docs/transformers/main/tasks/prompting) — Introduction; Best practices; Few-shot prompting and chat templates. Проверено: 2026-11-16.

## `hf-sft` — [SFT Trainer](https://huggingface.co/docs/trl/sft_trainer)

Hugging Face TRL. Проверено: 2026-11-16. Прочитано: Overview; Expected dataset type and format.

Обучение на примерах; language-modeling и prompt-completion datasets; conversational format и chat template.

Граница применения: В игре SFT объясняется на небольших примерах: полноценное дообучение внешней LLM не требуется.

- [Chat templates](https://huggingface.co/docs/transformers/chat_templating) — Token sequence; roles and control tokens; model-specific templates. Проверено: 2026-11-16.

## `peft-lora` — [LoRA](https://huggingface.co/docs/peft/v0.21.0/package_reference/lora)

Hugging Face PEFT. Проверено: 2026-11-16. Прочитано: LoRA usage; rank and alpha; LoraConfig parameter reference.

Ранг адаптера, target_modules, lora_alpha и число обучаемых параметров.

Граница применения: Конкретные названия target_modules зависят от архитектуры; адаптеры должны соответствовать базовой модели.

## `qlora-paper` — [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314)

Dettmers et al.. Проверено: 2026-11-16. Прочитано: Abstract.

Замороженная 4-bit база и обучаемые LoRA-адаптеры; NF4, double quantization, paged optimizers.

Граница применения: Показатели статьи относятся к её экспериментам; гарантия одинакового качества для любой модели не следует из результатов.

## `dpo-paper` — [Direct Preference Optimization: Your Language Model is Secretly a Reward Model](https://arxiv.org/abs/2305.18290)

Rafailov et al.. Проверено: 2026-11-16. Прочитано: Abstract.

Обучение по парам предпочтений; отличие DPO от SFT и от схемы с отдельной reward model и PPO.

Граница применения: Предпочтение в датасете не является гарантией объективной истинности или безопасности ответа.

## `hf-quantization` — [Quantization overview](https://huggingface.co/docs/transformers/quantization/overview)

Hugging Face. Проверено: 2026-11-16. Прочитано: Overview; Two ways to use a quantized model; Quantize a model while loading.

Меньшая битность весов/активаций; компромисс памяти, скорости и качества; загрузка квантованных checkpoints. GGUF как формат контейнера, а не отдельная битность.

Граница применения: Память на веса не равна полной RAM/VRAM: есть cache, activations, metadata и runtime. Ускорение зависит от железа и kernels.

- [GGUF specification](https://raw.githubusercontent.com/ggml-org/ggml/master/docs/gguf.md) — Introduction; specification goals; metadata. Проверено: 2026-11-16.

## `distillation` — [Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531)

Hinton, Vinyals and Dean. Проверено: 2026-11-16. Прочитано: Abstract.

Передача поведения teacher/ensemble компактному student; отличие от уменьшения битности.

Граница применения: Distillation требует обучения student; маленькая модель не обязана сохранять все способности teacher.

## `rag-paper` — [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)

Lewis et al.. Проверено: 2026-11-16. Прочитано: Abstract.

Комбинация параметрической модели с внешним индексом и retrieval; проверяемая опора на найденные документы.

Граница применения: Современный RAG шире конкретной архитектуры статьи. Retrieval не гарантирует релевантность или правильную интерпретацию.

Дополнительно прочитаны:

- [Retrieve & Re-Rank](https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html) — Retrieve & Re-Rank Pipeline; Bi-Encoder; Cross-Encoder; paragraph example. Проверено: 2026-11-16.
- [RAG in Transformers](https://huggingface.co/docs/transformers/model_doc/rag) — Introduction; conditioning generation on passages; index updates. Проверено: 2026-11-16.

## `agent-react` — [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)

Yao et al.. Проверено: 2026-11-16. Прочитано: Abstract.

Цикл выбора действия, обращения к инструменту, наблюдения и следующего решения.

Граница применения: Учебный симулятор показывает видимые действия и наблюдения; не выдаёт детерминированную цепочку карточек за работающую автономную LLM.

Дополнительно прочитаны:

- [Building effective agents](https://www.anthropic.com/research/building-effective-agents) — What are agents?; When to use agents; Parallelization; Orchestrator-workers; Agents. Проверено: 2026-11-16.

## `mcp-tools` — [Tools — Model Context Protocol](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)

Model Context Protocol. Проверено: 2026-11-16. Прочитано: User interaction model; capabilities; protocol messages; tool data types.

Имена инструментов, JSON Schema, tools/list, tools/call, результаты и ошибки. Resources дают контекст, адресованный URI.

Граница применения: Прочитана версия спецификации 2025-06-18. MCP стандартизует интерфейс, но не создаёт интеллект агента и не делает сервер доверенным.

- [Resources — Model Context Protocol](https://modelcontextprotocol.io/specification/2025-06-18/server/resources) — Resources, URIs, application-driven model; resources/list and resources/read. Проверено: 2026-11-16.

## `lm-eval` — [Language Model Evaluation Harness](https://github.com/EleutherAI/lm-evaluation-harness)

EleutherAI. Проверено: 2026-11-16. Прочитано: README: Overview; Basic Usage; backend table.

Воспроизводимые наборы задач, prompt/config, метрики и сравнение моделей.

Граница применения: Игра учит принципам оценки; она не запускает полный lm-evaluation-harness и не присваивает своим мини-задачам статус benchmark.

## `llm-judge` — [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)

Zheng et al.. Проверено: 2026-11-16. Прочитано: Abstract.

Ограничения LLM-оценщика: смещение по позиции, многословию, собственной модели и ограничения рассуждений.

Граница применения: Оценка по рубрике и сверка с человеком необходимы; результат одного оценщика не абсолютная истина.

## `vllm-serving` — [OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)

vLLM. Проверено: 2026-11-16. Прочитано: Introduction; Supported APIs; extra request parameters.

HTTP-serving; /v1/chat/completions; зависимость Chat API от chat template; отличие model weights от inference server. Continuous batching заполняет освободившиеся места запросами между шагами генерации.

Граница применения: Прочитан интерфейс HTTP, не подтверждена установка vLLM на Windows пользователя. Для игры сервер необязателен; соединение только localhost.

- [Continuous batching — Transformers](https://huggingface.co/docs/transformers/continuous_batching) — Introduction; scheduling requests at generation steps. Проверено: 2026-11-16.

Дополнительно прочитаны:

- [Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/) — Introduction; Example workloads; Limits (prefill reuse, not faster decode). Проверено: 2026-11-16.

## `skill-feel` — [maximizing-game-feel / SKILL.md](https://github.com/abagames/agentic-gamedev-skills/blob/main/.agents/skills/maximizing-game-feel/SKILL.md)

abagames. Проверено: 2026-11-16. Прочитано: Полный SKILL.md.

Сдержанная обратная связь, читаемость, честные границы объектов, сохранение отклика.

Граница применения: Справочный материал; внешние скрипты не установлены и не запускались. Полезен для полировки работающей игры, не заменяет игровой цикл.

## `skill-design` — [game-design / SKILL.md](https://github.com/saschb2b/skills/blob/main/skills/productivity/game-design/SKILL.md)

saschb2b. Проверено: 2026-11-16. Прочитано: Полный SKILL.md.

Осмысленный выбор, самостоятельная ценность core loop, обучение и читаемость интерфейса.

Граница применения: Не приняты предложения автоматически внедрять hooks/CLAUDE.md, обязательные согласования и категоричные жанровые правила. Использован как критически прочитанная справка.

## `skill-browser-feel` — [game-feel / SKILL.md](https://github.com/xhuozhong/codex-game-studio/blob/main/skills/game-feel/SKILL.md)

xhuozhong. Проверено: 2026-11-16. Прочитано: Полный SKILL.md.

Проверка реальным вводом, отклик перед декором, reduced motion, ограничения browser audio.

Граница применения: Короткий общий чеклист; не самостоятельная методология и не доказательство качества готовой игры.
## `instructgpt-paper` — [Training language models to follow instructions with human feedback](https://arxiv.org/html/2203.02155v1)

Ouyang et al., 2022. Проверено: 2026-11-16. Прочитано: Abstract; Introduction; §3.1 High-level methodology; начало §5.3 Limitations.

Один конкретный RLHF pipeline: SFT demonstrations → preference comparisons/reward model → PPO; границы представительности human feedback.

Граница применения: Описан метод InstructGPT, а не универсальная обязательная последовательность всех preference methods. Предпочтения оценщиков не равны истине или единому набору человеческих ценностей.

## `corrigibility-paper` — [Corrigibility](https://intelligence.org/files/Corrigibility.pdf)

Soares et al., AAAI Workshop 2015. Проверено: 2026-11-16. Прочитано: Abstract; §1 Introduction; §1.1 Corrigibility.

Краткий контекст: система должна допускать исправление и остановку; простая кнопка и лимит цикла не решают общую исследовательскую проблему.

Граница применения: Теоретическое введение и формальные постановки. В игре только распознавание понятия, без доказательства corrigibility или заявлений о сознании моделей.

## Как использованы материалы

Официальная документация служит опорой для терминов и поведения API. Статьи дают первичное описание методов, но их экспериментальные результаты не перенесены на учебные примеры как обещания. Для статей, где указан Abstract, проверено только заявленное описание метода; это не помечено как полный разбор работы.

Навыки GitHub читались как недоверенные внешние материалы. Их инструкции не получают приоритет над заказом и локальным контрактом. Никакие hooks, агенты, исполняемые файлы или внешние модели из этих репозиториев не устанавливались. Проверены перечисленные файлы, не безопасность всех репозиториев целиком.

В игре отсутствуют внешние изображения, музыка, фрагменты авторских курсов и датасеты заказчика. Мини-данные, текст, история и иллюстрации созданы для этой игры.


## Дополнения редакции V2

### Lensa ML

https://lensaml.com/

Прочитано: Главная страница, карта направлений и визуальный подход; полный сайт не прочитан.

Применение: Показывать связь изменения параметра с наблюдаемым результатом и явные предпосылки.

Граница: Ссылка для дополнительного изучения; тексты и визуальные компоненты сайта не включены в игру.

### Building AI Agents with Open Source Models — Mobile

https://agenticai.varasrinivas.com/courses/opensource/mobile/index.html

Прочитано: Главный каталог мобильных модулей; не заявляется прочтение всех карточек.

Применение: Связать понятия, схему агентного цикла, ошибки и отдельную практическую реализацию.

Граница: Это ресурс из списка пользователя. Выполняемые упражнения игры написаны самостоятельно.

### Introduction to PyTorch

https://uvadlc-notebooks.readthedocs.io/en/latest/tutorial_notebooks/tutorial2/Introduction_to_PyTorch.html

Прочитано: Введение, воспроизводимость через seed, начало раздела Tensors.

Применение: Явные предпосылки к тензорам и воспроизводимым экспериментам.

Граница: Игра закрепляет PyTorch2.8; указанные в учебнике версии среды не копируются как актуальные требования.

### Game design review skill

https://github.com/Yuki001/game-dev-skills/blob/main/skills/game-design-review/SKILL.md

Прочитано: SKILL.md и references: puzzles-and-problem-solving, interface-feedback-and-accessibility, experience-and-audience.

Применение: Задачи из уже показанной информации, ясная обратная связь и восстановление после ошибки.

Граница: Внешние инструкции оценивались критически; scripts/hooks не запускались.

### 2D games skill

https://github.com/agent-skills-hub/agent-skills-hub/blob/main/skills/game-development/2d-games/SKILL.md

Прочитано: SKILL.md — слои, атласы, взаимодействие и камера.

Применение: Разделение иллюстрированного фона и интерактивных элементов.

Граница: Рекомендации не являются оценкой качества готовой игры; внешний исполняемый код не использовался.

