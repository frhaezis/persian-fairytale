"""Original CPU exercises for The Game. Learner code is executed by runner.py.

No code-pattern grading: validators call functions on several inputs and inspect
values, shapes, gradients and model behaviour. `solution` is authoring material,
never returned by public_exercises(). Public feedback does not claim to assess
the learner's unrestricted prose or conceptual understanding.
"""
from __future__ import annotations

import math
import textwrap
import json
from pathlib import Path


def _code(value):
    return textwrap.dedent(value).strip() + "\n"


def _exercise(title, description, starter, solution, hint, torch=False):
    return dict(title=title, description=description, starter=_code(starter),
                solution=_code(solution), hint=hint, requiresTorch=torch)


EXERCISES = {
    "metrics": _exercise(
        "Четыре числа у городских ворот",
        "Напишите classification_metrics(y_true, y_pred). Верните dict: tp, fp, fn, tn, precision, recall, f1, accuracy. Метка 1 — опасный пропуск, который следует задержать. Если знаменатель равен нулю, метрика равна 0. Для пустого набора accuracy тоже 0. Не меняйте входные списки.",
        '''
        def classification_metrics(y_true, y_pred):
            # Пример: истина [1, 1, 0], решение [1, 0, 1].
            # Здесь TP=1, FN=1, FP=1, TN=0.
            tp = fp = fn = tn = 0
            for truth, prediction in zip(y_true, y_pred):
                # TODO: увеличьте один из четырёх счётчиков.
                pass
            # TODO: precision = TP/(TP+FP); recall = TP/(TP+FN).
            return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                    "precision": 0, "recall": 0, "f1": 0, "accuracy": 0}

        print(classification_metrics([1, 1, 0], [1, 0, 1]))
        ''',
        '''
        def classification_metrics(y_true, y_pred):
            tp = sum(t == 1 and p == 1 for t, p in zip(y_true, y_pred))
            fp = sum(t == 0 and p == 1 for t, p in zip(y_true, y_pred))
            fn = sum(t == 1 and p == 0 for t, p in zip(y_true, y_pred))
            tn = sum(t == 0 and p == 0 for t, p in zip(y_true, y_pred))
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=precision,
                        recall=recall, f1=f1,
                        accuracy=(tp + tn) / len(y_true) if y_true else 0.0)
        print(classification_metrics([1, 1, 0], [1, 0, 1]))
        ''',
        "Recall отвечает: какую долю опасных пропусков обнаружили? Его знаменатель TP+FN. Precision: какая доля задержанных действительно опасна? TP+FP. FP — задержали честного, FN — пропустили опасного. F1 — гармоническое среднее, не обычное арифметическое."),
    "regularization": _exercise(
        "Вес, которому нельзя расти бесконечно",
        "Для модели y_hat = w*x без свободного члена напишите ridge_weight(xs, ys, lam). Минимизируем SUM((w*x-y)^2) + lam*w^2, поэтому w = SUM(x*y)/(SUM(x*x)+lam). Сравните train и validation MSE для lam=0, 2, 20; затем измените SEED для другого шума train. Если знаменатель 0, верните 0. Отрицательную lam отвергайте ValueError. Валидацию выбирают отдельно от train.",
        '''
        def ridge_weight(xs, ys, lam):
            # lam — сила L2 regularization; x и y одинаковой длины.
            # TODO: запретите отрицательную lam и вычислите две суммы.
            return 0.0

        import random
        SEED = 7  # Затем попробуйте 19. Это синтетический шум, не новый test set.
        rng = random.Random(SEED)
        xs = [1.0, 2.0, 3.0]
        ys = [2*x + rng.gauss(0, 2.5) for x in xs]
        for lam in [0, 2, 20]:
            w = ridge_weight(xs, ys, lam)
            train_mse = sum((w*x-y)**2 for x, y in zip(xs, ys)) / len(xs)
            validation_mse = sum((w*x - 2*x)**2 for x in [1.5, 2.5, 4]) / 3
            print("seed", SEED, "lambda", lam, "weight", round(w, 3),
                  "train MSE", round(train_mse, 3), "validation MSE", round(validation_mse, 3))
        ''',
        '''
        def ridge_weight(xs, ys, lam):
            if lam < 0:
                raise ValueError("lam должна быть неотрицательной")
            denominator = sum(x*x for x in xs) + lam
            return sum(x*y for x, y in zip(xs, ys)) / denominator if denominator else 0.0

        import random
        SEED = 7
        rng = random.Random(SEED)
        xs = [1., 2., 3.]
        ys = [2*x + rng.gauss(0, 2.5) for x in xs]
        for lam in [0, 2, 20]:
            w = ridge_weight(xs, ys, lam)
            train = sum((w*x-y)**2 for x,y in zip(xs,ys)) / len(xs)
            val = sum((w*x - 2*x)**2 for x in [1.5, 2.5, 4]) / 3
            print("seed", SEED, "lambda", lam, "weight", round(w, 3),
                  "train MSE", round(train, 3), "validation MSE", round(val, 3))
        ''',
        "Увеличение lambda уменьшает |w|. Это воздействие на обучение, а не метрика и не обещание меньшей ошибки. Слишком большая lambda ведёт к underfitting. Здесь SUM loss: при MEAN loss масштаб lambda отличался бы."),
    "array_scan": _exercise(
        "Цена каравана — первая проба на 15 минут",
        "Напишите best_gain(prices): наибольшая неотрицательная прибыль от одной покупки и более поздней продажи. Покупка не обязательна. Для пустого списка, одного дня или падающих цен верните 0. Постарайтесь использовать один проход и O(1) дополнительной памяти.",
        '''
        def best_gain(prices):
            # [7, 1, 5, 3, 6, 4] -> 5: купить за 1, продать за 6.
            # TODO: храните минимальную цену СРЕДИ УЖЕ встреченных.
            return 0

        print(best_gain([7, 1, 5, 3, 6, 4]))
        ''',
        '''
        def best_gain(prices):
            lowest = float("inf")
            best = 0
            for price in prices:
                best = max(best, price - lowest)
                lowest = min(lowest, price)
            return best
        print(best_gain([7, 1, 5, 3, 6, 4]))
        ''',
        "Сначала проверьте: можно ли выгодно продать сегодня? Затем обновите минимальную цену. Ответ для [5, 4, 3] равен 0, а не -1."),
    "tensors": _exercise(
        "Слитки чисел",
        "Напишите make_tensor(rows): из вложенного прямоугольного списка создайте настоящий CPU torch.Tensor с dtype=torch.float32. Сохраните значения и форму. Список [] допустим: shape будет (0,). Изучите shape, dtype и device, затем измените входные числа.",
        '''
        import torch

        def make_tensor(rows):
            # TODO: torch.tensor(..., dtype=..., device=...)
            return rows

        result = make_tensor([[1, 2], [3, 4]])
        print(result)
        print("shape:", getattr(result, "shape", "пока это список"))
        ''',
        '''
        import torch
        def make_tensor(rows):
            return torch.tensor(rows, dtype=torch.float32, device="cpu")
        result = make_tensor([[1, 2], [3, 4]])
        print(result, result.shape, result.dtype, result.device)
        ''',
        "Tensor — многомерный массив с операциями и возможностью autograd. Числа по умолчанию могут дать int64; для обучения здесь явно выберите torch.float32.", True),
    "shapes": _exercise(
        "Провода и оси",
        "Напишите row_means(x), где x — двумерный float tensor [batch, features]. Верните среднее каждой строки с shape [batch], сохранив dtype и возможность передачи gradient. Проверьте, почему dim=0 даёт другой смысл.",
        '''
        import torch
        def row_means(x):
            # [[2, 4, 6], [1, 1, 4]] -> tensor([4., 2.])
            # TODO: усредните features, то есть dim=1.
            return x
        print(row_means(torch.tensor([[2., 4., 6.], [1., 1., 4.]])))
        ''',
        '''
        import torch
        def row_means(x):
            return x.mean(dim=1)
        print(row_means(torch.tensor([[2., 4., 6.], [1., 1., 4.]])))
        ''',
        "В shape [2, 3] первая ось перебирает два объекта, вторая — три признака. mean(dim=1) убирает ось признаков: остаётся shape [2]. Не превращайте tensor в список или numpy: так потеряется autograd.", True),
    "autograd": _exercise(
        "След изменения",
        "Напишите polynomial_grad(x). x — leaf tensor с requires_grad=True и пустым .grad. Постройте y=SUM(x**3-x**2), вызовите backward и верните x.grad. Не задавайте градиент вручную. Проверка смотрит и возвращённое значение, и накопленный .grad. Объясните знак derivative для разных x.",
        '''
        import torch
        def polynomial_grad(x):
            y = (x**3 - x**2).sum()
            # TODO: запустите обратное распространение от scalar y.
            return x.grad
        x = torch.tensor([1., 2., -1.], requires_grad=True)
        print(polynomial_grad(x))
        ''',
        '''
        import torch
        def polynomial_grad(x):
            y = (x**3 - x**2).sum()
            y.backward()
            return x.grad
        x = torch.tensor([1., 2., -1.], requires_grad=True)
        print(polynomial_grad(x))
        ''',
        "Derivative x³−x² равна 3x²−2x. backward() идёт по computational graph и накапливает gradient в leaf tensor. В этом упражнении x свежий; при обучении старые gradients необходимо очищать.", True),
    "module": _exercise(
        "Маленький искусственный механизм",
        "Напишите build_model(), возвращающую nn.Module, который принимает float tensor [batch,2] и выдаёт [batch,1]. Нужен обучаемый linear layer с bias. forward должен зависеть от входа; параметры должны получать gradient. Величины случайных начальных weights не оцениваются.",
        '''
        import torch
        from torch import nn

        class Lantern(nn.Module):
            def __init__(self):
                super().__init__()
                # TODO: self.linear = nn.Linear(in_features, out_features)
            def forward(self, x):
                # TODO: используйте свой слой.
                return x

        def build_model():
            return Lantern()

        print(build_model()(torch.tensor([[1., 2.], [3., 4.]])))
        ''',
        '''
        import torch
        from torch import nn
        class Lantern(nn.Module):
            def __init__(self):
                super().__init__()
                self.linear = nn.Linear(2, 1)
            def forward(self, x):
                return self.linear(x)
        def build_model():
            return Lantern()
        print(build_model()(torch.tensor([[1., 2.], [3., 4.]])))
        ''',
        "nn.Module регистрирует вложенные слои и параметры. nn.Linear(2,1) хранит matrix weight [1,2] и bias [1]. Используйте model(x), а не прямой вызов forward: так сохраняются механизмы Module.", True),
    "losses": _exercise(
        "Что именно считать ошибкой",
        "Напишите loss_for(kind, predictions, targets). kind='classification': cross-entropy для raw logits [batch,classes] и индексов классов int64. kind='regression': mean squared error. Верните scalar tensor с gradient. Не делайте softmax перед cross_entropy. Для неизвестного kind выбросите ValueError.",
        '''
        import torch
        import torch.nn.functional as F
        def loss_for(kind, predictions, targets):
            if kind == "classification":
                # TODO: F.cross_entropy получает logits.
                return predictions.sum() * 0
            if kind == "regression":
                # TODO: F.mse_loss
                return predictions.sum() * 0
            raise ValueError("Неизвестный kind")
        logits = torch.tensor([[2., -1.], [-2., 3.]], requires_grad=True)
        print(loss_for("classification", logits, torch.tensor([0, 1])))
        ''',
        '''
        import torch
        import torch.nn.functional as F
        def loss_for(kind, predictions, targets):
            if kind == "classification":
                return F.cross_entropy(predictions, targets)
            if kind == "regression":
                return F.mse_loss(predictions, targets)
            raise ValueError("Неизвестный kind")
        logits = torch.tensor([[2., -1.], [-2., 3.]], requires_grad=True)
        print(loss_for("classification", logits, torch.tensor([0, 1])))
        ''',
        "Cross-entropy внутри использует log-softmax; повторный softmax изменит задачу. MSE сравнивает численные значения. Contrastive loss учит близости/различию представлений; он нужен для другой постановки, а не вместо любой loss.", True),
    "optimizer": _exercise(
        "Один честный шаг обучения",
        "Напишите train_step(model,x,y,optimizer): переведите model в train, очистите старые gradients, вычислите MSE, выполните backward и optimizer.step. Верните float значения loss ДО изменения параметров. Проверка подмешивает старый gradient, чтобы обнаружить пропущенный zero_grad.",
        '''
        import torch
        import torch.nn.functional as F
        def train_step(model, x, y, optimizer):
            model.train()
            # TODO: очистка gradients
            loss = F.mse_loss(model(x), y)
            # TODO: backward, затем шаг optimizer
            return loss.item()

        model = torch.nn.Linear(1, 1)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
        x = torch.tensor([[1.], [2.], [3.]])
        y = 2*x + 1
        for step in range(3):
            print("step", step, "loss", train_step(model, x, y, optimizer))
        ''',
        '''
        import torch
        import torch.nn.functional as F
        def train_step(model, x, y, optimizer):
            model.train()
            optimizer.zero_grad()
            loss = F.mse_loss(model(x), y)
            loss.backward()
            optimizer.step()
            return loss.item()
        model = torch.nn.Linear(1, 1)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
        x = torch.tensor([[1.], [2.], [3.]])
        y = 2*x + 1
        for step in range(3):
            print("step", step, "loss", train_step(model, x, y, optimizer))
        ''',
        "Порядок: zero_grad → forward/loss → backward → step. backward вычисляет gradients, step изменяет параметры. zero_grad очищает накопление с прошлого шага; model.train() его не заменяет.", True),
    "modes": _exercise(
        "Проверка без случайной завесы",
        "Напишите predict(model,x): установите eval mode и вычислите результат внутри torch.no_grad(). Верните tensor. Состояние model оставьте eval. Разберитесь: eval изменяет поведение Dropout/BatchNorm, no_grad отключает запись computational graph. Это две разные операции.",
        '''
        import torch
        def predict(model, x):
            # TODO: eval + контекст no_grad, затем model(x).
            return model(x)

        model = torch.nn.Sequential(torch.nn.Linear(2, 2), torch.nn.Dropout(0.8))
        x = torch.tensor([[1., 2.]], requires_grad=True)
        print(predict(model, x))
        ''',
        '''
        import torch
        def predict(model, x):
            model.eval()
            with torch.no_grad():
                return model(x)
        model = torch.nn.Sequential(torch.nn.Linear(2, 2), torch.nn.Dropout(0.8))
        x = torch.tensor([[1., 2.]], requires_grad=True)
        print(predict(model, x))
        ''',
        "model.eval() не запрещает вычисление gradients. torch.no_grad() не выключает Dropout. Для этой проверки нужны оба: правильное поведение слоёв и отсутствие графа.", True),
    "training": _exercise(
        "Опыт, который переживает новые данные",
        "Напишите fit_line(x_train,y_train,x_validation,y_validation). Данные — float tensors [n,1]. Обучите nn.Linear(1,1) только на train, затем верните dict {model,train_loss,val_loss}; обе loss — float MSE. Сбросьте seed в функции. Validation labels участвуют только в измерении. Меняйте число шагов и learning rate и объясняйте изменения.",
        '''
        import torch
        import torch.nn.functional as F
        def fit_line(x_train, y_train, x_validation, y_validation):
            torch.manual_seed(7)
            model = torch.nn.Linear(1, 1)
            optimizer = torch.optim.SGD(model.parameters(), lr=0.08)
            for _ in range(250):
                # TODO: train → zero_grad → loss на TRAIN → backward → step
                pass
            model.eval()
            with torch.no_grad():
                train_loss = F.mse_loss(model(x_train), y_train).item()
                val_loss = F.mse_loss(model(x_validation), y_validation).item()
            return {"model": model, "train_loss": train_loss, "val_loss": val_loss}

        x = torch.tensor([[-2.], [-1.], [0.], [1.], [2.]])
        xv = torch.tensor([[-1.5], [0.5], [1.5]])
        result = fit_line(x, 2*x+1, xv, 2*xv+1)
        print("train:", result["train_loss"], "validation:", result["val_loss"])
        ''',
        '''
        import torch
        import torch.nn.functional as F
        def fit_line(x_train, y_train, x_validation, y_validation):
            torch.manual_seed(7)
            model = torch.nn.Linear(1, 1)
            optimizer = torch.optim.SGD(model.parameters(), lr=0.08)
            model.train()
            for _ in range(250):
                optimizer.zero_grad()
                loss = F.mse_loss(model(x_train), y_train)
                loss.backward()
                optimizer.step()
            model.eval()
            with torch.no_grad():
                train_loss = F.mse_loss(model(x_train), y_train).item()
                val_loss = F.mse_loss(model(x_validation), y_validation).item()
            return {"model": model, "train_loss": train_loss, "val_loss": val_loss}
        x = torch.tensor([[-2.], [-1.], [0.], [1.], [2.]])
        xv = torch.tensor([[-1.5], [0.5], [1.5]])
        result = fit_line(x, 2*x+1, xv, 2*xv+1)
        print("train:", result["train_loss"], "validation:", result["val_loss"])
        ''',
        "Вычислите loss внутри цикла по x_train,y_train. После цикла отдельно измерьте validation под no_grad. Успех на этой простой прямой не гарантирует generalization в другой задаче; эксперимент проверяет процедуру.", True),
    "normalization": _exercise(
        "Контролируемый опыт: нормализация и Dropout",
        "Готовая normalize_rows(x) показывает LayerNorm по последней оси без обучаемых scale/bias, eps=1e-5; её можно исследовать. Допишите build_dropout_model(p): CPU nn.Sequential из Linear(2,16), ReLU, Dropout(p), Linear(16,1). Допишите evaluate_mse(model,x,y): переведите модель в eval, измерьте среднюю квадратичную ошибку внутри torch.no_grad() и верните float, оставив модель в eval. Проверка обучит три ваши сети с p=0, 0.2, 0.8 на одинаковом разбиении и из одинаковых начальных весов. Графики показывают настоящие измерения; улучшение от Dropout не гарантируется. Перед каждым шагом обучения учебный стенд сам вызывает train().",
        '''
        import torch
        import torch.nn.functional as F
        def normalize_rows(x):
            return F.layer_norm(x, (x.shape[-1],), eps=1e-5)

        def build_dropout_model(p):
            # Порядок слоёв: Linear(2,16) → ReLU → Dropout(p) → Linear(16,1).
            # TODO: верните torch.nn.Sequential с этими слоями.
            return torch.nn.Identity()

        def evaluate_mse(model, x, y):
            # TODO: eval; with torch.no_grad(); F.mse_loss(...).item().
            return 0.0

        print(normalize_rows(torch.tensor([[1., 2., 3.], [10., 20., 30.]])))
        # После исправления функций кнопка «Запустить» обучит три сети
        # на учебных данных и покажет графики train/validation.
        ''',
        '''
        import torch
        import torch.nn.functional as F
        def normalize_rows(x):
            return F.layer_norm(x, (x.shape[-1],), eps=1e-5)
        def build_dropout_model(p):
            return torch.nn.Sequential(torch.nn.Linear(2, 16), torch.nn.ReLU(),
                                       torch.nn.Dropout(p), torch.nn.Linear(16, 1))
        def evaluate_mse(model, x, y):
            model.eval()
            with torch.no_grad():
                return F.mse_loss(model(x), y).item()
        print(normalize_rows(torch.tensor([[1., 2., 3.], [10., 20., 30.]])))
        ''',
        "Sequential вызывает слои по порядку; число выходов одного Linear равно числу входов следующего. Dropout(p) обнуляет активации случайно только в train. evaluate_mse использует и eval(), и no_grad(): первое меняет поведение слоёв, второе отключает граф. LayerNorm нормирует строку, а не выключает элементы; это другой механизм.", True),
    "two_sum": _exercise(
        "Два груза — вторая проба на 15 минут",
        "Напишите two_sum(nums,target). Верните индексы двух РАЗНЫХ элементов с нужной суммой, либо [] если пары нет. Любая правильная пара подходит; вход не меняйте. Храните ранее увиденные числа в hash map и добейтесь ожидаемого O(n).",
        '''
        def two_sum(nums, target):
            seen = {}
            for i, value in enumerate(nums):
                # TODO: нужен target-value. Проверьте ДО добавления value.
                pass
            return []
        print(two_sum([2, 7, 11, 15], 9))
        ''',
        '''
        def two_sum(nums, target):
            seen = {}
            for i, value in enumerate(nums):
                if target - value in seen:
                    return [seen[target - value], i]
                seen[value] = i
            return []
        print(two_sum([2, 7, 11, 15], 9))
        ''',
        "Число может повторяться: [3,3], target=6 → [0,1]. Нельзя использовать индекс дважды. Сначала ищите дополнение среди прошлых чисел, потом запоминайте текущее."),
    "agent_loop": _exercise(
        "Джинн, умеющий остановиться",
        "Напишите navigate(call_tool,start,target,budget). Пока позиция не равна target и есть budget, вызовите call_tool('step', {'position':position,'delta':±1}) и прочитайте возвращённый {'position':...}. Верните {'position':int,'calls':int,'reason':'goal' либо 'budget'}. Это явно детерминированный test double, не ответ LLM. Нельзя просто присвоить target без tool call.",
        '''
        def navigate(call_tool, start, target, budget):
            position, calls = start, 0
            # TODO: ограниченный loop, tool request → result → update → stop.
            return {"position": position, "calls": calls,
                    "reason": "goal" if position == target else "budget"}

        def demo_tool(name, args):
            print("tool request:", name, args)
            return {"position": args["position"] + args["delta"]}
        print(navigate(demo_tool, 0, 3, 5))
        ''',
        '''
        def navigate(call_tool, start, target, budget):
            position, calls = start, 0
            while position != target and calls < budget:
                delta = 1 if target > position else -1
                result = call_tool("step", {"position": position, "delta": delta})
                position = result["position"]
                calls += 1
            return {"position": position, "calls": calls,
                    "reason": "goal" if position == target else "budget"}
        def demo_tool(name, args):
            print("tool request:", name, args)
            return {"position": args["position"] + args["delta"]}
        print(navigate(demo_tool, 0, 3, 5))
        ''',
        "Условия остановки проверяются до следующего вызова. Даже если инструмент не сдвигает позицию, budget обязан завершить цикл. Результат инструмента — факт о мире; не подменяйте его ожиданием агента."),
    "brackets": _exercise(
        "Запечатанное письмо — третья проба на 15 минут",
        "Напишите balanced(text). Проверьте правильную вложенность (), [], {} с помощью stack. Другие символы игнорируйте. Пустая строка правильная. Например, '{a:[()]}' → True, '([)]' → False. Обоснуйте O(n) времени и O(n) памяти в худшем случае.",
        '''
        def balanced(text):
            stack = []
            opening = {"(": ")", "[": "]", "{": "}"}
            for char in text:
                # TODO: открывающий символ кладёт ожидаемую пару в stack;
                # закрывающий должен совпасть с последней ожидаемой парой.
                pass
            return len(stack) == 0
        print(balanced("{a:[()]}"), balanced("([)]"))
        ''',
        '''
        def balanced(text):
            stack = []
            opening = {"(": ")", "[": "]", "{": "}"}
            for char in text:
                if char in opening:
                    stack.append(opening[char])
                elif char in ")]}":
                    if not stack or stack.pop() != char:
                        return False
            return not stack
        print(balanced("{a:[()]}"), balanced("([)]"))
        ''',
        "Stack хранит ожидаемые закрывающие скобки. Одних равных количеств недостаточно: ([)] имеет правильные количества, но неверную вложенность."),
    "longest_unique": _exercise(
        "Последний маршрут — финальные 15 минут",
        "Напишите longest_unique(text): длина самого длинного непрерывного фрагмента без повторяющихся символов. Строка Unicode; пустая даёт 0. Примеры: 'abcabcbb'→3, 'bbbbb'→1. Начните с понятного корректного решения; затем используйте sliding window и last seen для O(n).",
        '''
        def longest_unique(text):
            # TODO: окно [left, right] с уникальными символами.
            # Повтор сдвигает left только вправо.
            return 0
        print(longest_unique("abcabcbb"))
        ''',
        '''
        def longest_unique(text):
            last_seen = {}
            left = best = 0
            for right, char in enumerate(text):
                if char in last_seen:
                    left = max(left, last_seen[char] + 1)
                last_seen[char] = right
                best = max(best, right - left + 1)
            return best
        print(longest_unique("abcabcbb"))
        ''',
        "Для 'abba' левая граница после второго b уже 2. При встрече последнего a её нельзя вернуть к 1: используйте max(left,last_seen[char]+1). Корректность важнее скорости печати."),
    "split": _exercise(
        "Один караван — одна выборка",
        "Напишите split_groups(rows,validation_groups,test_groups). Каждый row — dict с полями id и group. Все записи группы должны попасть в одну часть. Верните {'train':список,'validation':список,'test':список}, сохраняя исходный порядок. Пересечение validation_groups и test_groups — ValueError. Не меняйте rows.",
        '''
        def split_groups(rows, validation_groups, test_groups):
            result = {"train": [], "validation": [], "test": []}
            # TODO: проверьте пересечение групп и распределите записи.
            return result
        rows = [{"id": "a", "group": "north"}, {"id": "b", "group": "south"}]
        print(split_groups(rows, {"south"}, set()))
        ''',
        '''
        def split_groups(rows, validation_groups, test_groups):
            validation_groups, test_groups = set(validation_groups), set(test_groups)
            if validation_groups & test_groups:
                raise ValueError("Группа попала одновременно в validation и test")
            result = {"train": [], "validation": [], "test": []}
            for row in rows:
                key = "test" if row["group"] in test_groups else "validation" if row["group"] in validation_groups else "train"
                result[key].append(row)
            return result
        rows = [{"id": "a", "group": "north"}, {"id": "b", "group": "south"}]
        print(split_groups(rows, {"south"}, set()))
        ''',
        "Если близкие записи одного человека/каравана попадают и в train, и в validation, оценка может быть слишком оптимистичной. Разделяйте нужную независимую единицу, а не случайные строки."),
    "retrieval": _exercise(
        "Индекс улик",
        "Напишите retrieve(query,documents,k). document содержит id и text. Для простого lexical retrieval: lowercase, split по пробелам, уникальные токены; score — количество общих токенов с query. Оставьте score>0, отсортируйте по убыванию score, при равенстве по id и верните первые k ID. Это учебный baseline, не полноценный semantic search.",
        '''
        def retrieve(query, documents, k):
            query_tokens = set(query.lower().split())
            # TODO: пересечение множеств, сортировка, top-k.
            return []
        docs = [{"id": "a", "text": "синий фонарь"}, {"id": "b", "text": "красный фонарь у ворот"}]
        print(retrieve("синий фонарь", docs, 1))
        ''',
        '''
        def retrieve(query, documents, k):
            query_tokens = set(query.lower().split())
            scored = []
            for doc in documents:
                score = len(query_tokens & set(doc["text"].lower().split()))
                if score > 0:
                    scored.append((-score, doc["id"]))
            return [doc_id for _, doc_id in sorted(scored)[:max(0,k)]]
        docs = [{"id": "a", "text": "синий фонарь"}, {"id": "b", "text": "красный фонарь у ворот"}]
        print(retrieve("синий фонарь", docs, 1))
        ''',
        "Повтор слова не повышает score: используем set. Retrieval выбирает источники; generation формулирует ответ. Даже релевантный найденный текст нужно проверить на достоверность."),
    "attention": _exercise(
        "Один луч внимания",
        "Напишите attend(q,keys,values): q имеет shape [d], keys [n,d], values [n,v]. Верните weighted sum values с весами softmax((keys @ q)/sqrt(d)), shape [v]. Не делайте argmax: attention смешивает values. Нужны настоящие torch операции с gradient.",
        '''
        import torch
        import math
        def attend(q, keys, values):
            # TODO: scores → scaled scores → softmax по токенам → weighted sum.
            return values[0]
        q = torch.tensor([1., 0.])
        keys = torch.tensor([[1., 0.], [0., 1.]])
        values = torch.tensor([[10., 0.], [0., 10.]])
        print(attend(q, keys, values))
        ''',
        '''
        import torch
        import math
        def attend(q, keys, values):
            scores = (keys @ q) / math.sqrt(q.shape[-1])
            weights = torch.softmax(scores, dim=0)
            return weights @ values
        q = torch.tensor([1., 0.])
        keys = torch.tensor([[1., 0.], [0., 1.]])
        values = torch.tensor([[10., 0.], [0., 10.]])
        print(attend(q, keys, values))
        ''',
        "Q задаёт запрос, K участвуют в оценке совместимости, V несут смешиваемое содержимое. Деление на sqrt(d) ограничивает масштаб dot products. Это одна query и одна head, без mask; полноценный Transformer сложнее.", True),
    "gradient_descent": _exercise(
        "Склон ошибки",
        "Напишите descend(w,xs,ys,lr): один шаг gradient descent для MEAN((w*x-y)^2), модель без bias. Производная = 2*MEAN((w*x-y)*x). Верните новое w = w-lr*gradient. Пустой набор оставляет w без изменений. Сначала предскажите направление движения, затем запустите.",
        '''
        def descend(w, xs, ys, lr):
            # TODO: вычислите gradient и вычтите lr*gradient.
            return w
        w = 0.0
        for _ in range(5):
            w = descend(w, [1., 2.], [2., 4.], 0.1)
            print(w)
        ''',
        '''
        def descend(w, xs, ys, lr):
            if not xs:
                return w
            gradient = 2 * sum((w*x-y)*x for x, y in zip(xs, ys)) / len(xs)
            return w - lr*gradient
        w = 0.0
        for _ in range(5):
            w = descend(w, [1., 2.], [2., 4.], 0.1)
            print(w)
        ''',
        "Gradient указывает локальное направление увеличения loss; вычитаем его. Learning rate — размер шага. Слишком большой шаг может увеличить loss или вызвать расходимость, даже при правильной формуле."),
}


def public_exercises():
    """Return learner-facing metadata. Reference implementations stay private."""
    tutorials = json.loads((Path(__file__).resolve().parent / "data" / "exercise_teaching.json").read_text(encoding="utf-8"))
    return {key: {**{k: v for k, v in exercise.items() if k != "solution"},
                  "teaching": tutorials[key]}
            for key, exercise in EXERCISES.items()}


def _dropout_experiment(namespace, transfer=False):
    """Train candidate-created models. Every displayed point is an observed MSE."""
    import torch
    import torch.nn.functional as F
    seed = 43 if transfer else 41
    generator = torch.Generator().manual_seed(seed)
    x_train = torch.rand((12, 2), generator=generator) * 2 - 1
    x_validation = torch.rand((64, 2), generator=generator) * 2 - 1
    def target(x):
        return 1.4*x[:, :1] - .8*x[:, 1:] + .7*torch.sin(4*x[:, :1])
    y_train = target(x_train) + .35*torch.randn((12, 1), generator=generator)
    y_validation = target(x_validation)
    series = []
    outcomes = []
    initial = None
    for probability in (0., .2, .8):
        torch.manual_seed(seed + 100)
        model = namespace["build_dropout_model"](probability)
        weights = [p.detach().clone() for p in model.parameters()]
        if initial is None:
            initial = weights
        elif len(initial) != len(weights) or any(not torch.equal(a, b) for a, b in zip(initial, weights)):
            raise AssertionError("Для сравнения нужны одинаковые начальные weights при одинаковом seed")
        optimizer = torch.optim.SGD(model.parameters(), lr=.08)
        train_values, validation_values = [], []
        for epoch in range(41):
            if epoch:
                model.train()
                optimizer.zero_grad()
                loss = F.mse_loss(model(x_train), y_train)
                loss.backward()
                optimizer.step()
            a = namespace["evaluate_mse"](model, x_train, y_train)
            b = namespace["evaluate_mse"](model, x_validation, y_validation)
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (a, b)):
                raise AssertionError("История эксперимента должна состоять из конечных чисел MSE")
            train_values.append(float(a)); validation_values.append(float(b))
        steps = list(range(41))
        series.extend([{"label": f"p={probability:g} · train", "values": train_values, "steps": steps},
                       {"label": f"p={probability:g} · validation", "values": validation_values, "steps": steps}])
        outcomes.append(f"p={probability:g}: train MSE={train_values[-1]:.4f}; validation MSE={validation_values[-1]:.4f}.")
    return {"kind": "training-curves", "title": "Ваши сети: одинаковые данные и начальные веса",
            "xLabel": "Шаг обучения", "yLabel": "MSE", "series": series,
            "observations": outcomes + ["Train и validation измерены в eval: сравниваются одинаковые режимы без случайной маски.",
                "Это один небольшой синтетический опыт. Для устойчивого вывода повторите с другими seed; лучший p здесь не универсален."],
            "parameters": {"seed": seed, "trainingRows": 12, "validationRows": 64, "epochs": 40,
                           "learningRate": .08, "probabilities": [0, .2, .8],
                           "target": "1.4*x1 - 0.8*x2 + 0.7*sin(4*x1)", "trainNoiseStd": .35,
                           "measurementMode": "eval + no_grad", "source": "candidate functions executed by validator"}}


def validate(exercise_id, namespace, variant="practice"):
    """Evaluate outcomes. Fresh processes prevent cross-attempt Python state."""
    if exercise_id not in EXERCISES:
        return {"passed": False, "feedback": "Неизвестное упражнение.", "results": []}
    transfer = variant == "transfer"
    results = []
    artifact = None

    def check(label, work):
        try:
            work()
            results.append({"name": label, "passed": True, "detail": "Проверено на вычисленном результате."})
        except Exception as exc:
            results.append({"name": label, "passed": False,
                            "detail": f"{type(exc).__name__}: {str(exc)[:450]}"})

    def require(condition, message):
        if not condition:
            raise AssertionError(message)

    def close(actual, expected, message="Число не совпало", atol=1e-5):
        require(isinstance(actual, (int, float)) and not isinstance(actual, bool), "Ожидалось число Python")
        require(math.isfinite(float(actual)) and math.isclose(float(actual), float(expected), rel_tol=1e-4, abs_tol=atol),
                f"{message}: получено {actual}, ожидалось {expected:.6g}")

    def function(name):
        fn = namespace.get(name)
        require(callable(fn), f"Определите функцию {name} с именем из задания")
        return fn

    torch = None
    if EXERCISES[exercise_id]["requiresTorch"]:
        try:
            import torch as torch_module
            torch = torch_module
            torch.set_num_threads(1)
            torch.manual_seed(17 if transfer else 7)
        except ImportError:
            return {"passed": False, "feedback": "В этом интерпретаторе нет PyTorch. Установите зависимости или используйте запасной notebook.", "results": []}

    def tensor_close(actual, expected, message="Tensor отличается", atol=1e-5):
        require(isinstance(actual, torch.Tensor), "Нужен настоящий torch.Tensor")
        require(actual.shape == expected.shape, f"Неверный shape: {tuple(actual.shape)}, нужен {tuple(expected.shape)}")
        require(torch.isfinite(actual).all().item(), "В результате NaN или infinity")
        require(torch.allclose(actual.to(expected.dtype), expected, atol=atol, rtol=1e-4), message)

    if exercise_id == "metrics":
        cases = [([1,0,1,0,1,0],[1,1,0,0,1,0]), ([1,1,0,0],[1,0,0,0]), ([0,0],[0,0]), ([],[])] if not transfer else [([1,1,1,0],[0,0,0,0]), ([1,1,0],[1,1,1]), ([0,0,0],[1,1,1]), ([1,0,1],[1,0,1])]
        for i,(truth,pred) in enumerate(cases):
            def work(truth=truth,pred=pred):
                result = function("classification_metrics")(truth[:],pred[:])
                require(isinstance(result,dict), "Верните dict с четырьмя счётчиками и метриками")
                tp=sum(t==p==1 for t,p in zip(truth,pred)); tn=sum(t==p==0 for t,p in zip(truth,pred))
                fp=sum(t==0 and p==1 for t,p in zip(truth,pred)); fn=sum(t==1 and p==0 for t,p in zip(truth,pred))
                precision=tp/(tp+fp) if tp+fp else 0; recall=tp/(tp+fn) if tp+fn else 0
                expected=dict(tp=tp,fp=fp,fn=fn,tn=tn,precision=precision,recall=recall,
                              f1=2*precision*recall/(precision+recall) if precision+recall else 0,
                              accuracy=(tp+tn)/len(truth) if truth else 0)
                for key,value in expected.items(): close(result.get(key),value,key)
            check(f"Confusion matrix, случай {i+1}",work)
    elif exercise_id == "regularization":
        cases=[([1,2,3],[2,4,6],0),([1,2,3],[2,4,6],14),([0,0],[1,2],0)] if not transfer else [([-2,0,2],[-3,0,3],2),([1,1],[3,5],4),([],[],3)]
        for i,(xs,ys,lam) in enumerate(cases):
            def work(xs=xs,ys=ys,lam=lam):
                denom=sum(x*x for x in xs)+lam
                expected=sum(x*y for x,y in zip(xs,ys))/denom if denom else 0
                close(function("ridge_weight")(xs,ys,lam),expected,"Ridge weight")
            check(f"L2, случай {i+1}",work)
        def negative():
            try: function("ridge_weight")([1],[2],-1)
            except ValueError: return
            raise AssertionError("Отрицательная lambda должна вызывать ValueError")
        check("Неверная lambda",negative)
    elif exercise_id == "array_scan":
        cases=[([7,1,5,3,6,4],5),([5,4,3],0),([],0),([1],0)] if not transfer else [([2,1,2,0,1],1),([3,3,3],0),([1,10,0,2],9)]
        for i,(xs,answer) in enumerate(cases):
            def work(xs=xs,answer=answer):
                original=xs[:]; close(function("best_gain")(xs),answer,"Прибыль"); require(xs==original,"Не меняйте вход")
            check(f"Маршрут цен {i+1}",work)
    elif exercise_id == "tensors":
        cases=[[[1,2],[3,4]],[[0.25,-1.5,3.0]],[]] if not transfer else [[[2],[7],[-3]],[[1,2,3],[4,5,6]],[]]
        for i,rows in enumerate(cases):
            def work(rows=rows):
                actual=function("make_tensor")(rows)
                tensor_close(actual,torch.tensor(rows,dtype=torch.float32))
                require(actual.dtype==torch.float32,"Нужен dtype=torch.float32")
                require(actual.device.type=="cpu","Обязательная задача работает на CPU")
            check(f"Tensor {i+1}",work)
    elif exercise_id == "shapes":
        cases=[[[2.,4.,6.],[1.,1.,4.]],[[1.],[7.],[-2.]],[[0.,2.]]] if not transfer else [[[3.,-3.],[10.,4.],[0.,0.]],[[1.,2.,4.,9.]]]
        for i,rows in enumerate(cases):
            def work(rows=rows):
                x=torch.tensor(rows,requires_grad=True)
                actual=function("row_means")(x)
                tensor_close(actual,x.mean(1))
                require(actual.requires_grad,"Потерян computational graph")
                actual.sum().backward()
                tensor_close(x.grad,torch.full_like(x,1/x.shape[1]),"Неверный gradient по оси")
            check(f"Ось и gradient {i+1}",work)
    elif exercise_id == "autograd":
        cases=[[1.,2.,-1.],[0.,.5],[-2.]] if not transfer else [[-3.,1.5,0.],[2./3.,4.]]
        for i,values in enumerate(cases):
            def work(values=values):
                x=torch.tensor(values,requires_grad=True); expected=3*x.detach()**2-2*x.detach()
                actual=function("polynomial_grad")(x)
                tensor_close(actual,expected,"Проверьте формулу x**3-x**2 и backward")
                require(x.grad is not None,"Gradient не накопился в x.grad")
                tensor_close(x.grad,expected)
            check(f"Обратное распространение {i+1}",work)
    elif exercise_id == "module":
        for batch in ([1,4,2] if not transfer else [3,7]):
            def work(batch=batch):
                model=function("build_model")()
                require(isinstance(model,torch.nn.Module),"Верните nn.Module")
                params=list(model.parameters()); require(bool(params),"Нет зарегистрированных параметров")
                require(any(tuple(p.shape)==(1,2) for p in params),"Нужен Linear weight [1,2]")
                require(any(tuple(p.shape)==(1,) for p in params),"Нужен обучаемый bias [1]")
                x=torch.arange(batch*2,dtype=torch.float32).reshape(batch,2)+0.3
                out=model(x); require(isinstance(out,torch.Tensor) and tuple(out.shape)==(batch,1),"Выход должен иметь shape [batch,1]")
                out.sum().backward()
                require(all(p.grad is not None and torch.isfinite(p.grad).all().item() for p in params if p.requires_grad),"Все обучаемые параметры должны получить gradient")
                weight=next(p for p in params if tuple(p.shape)==(1,2))
                tensor_close(weight.grad,x.sum(0,keepdim=True),"Выход должен использовать linear layer")
            check(f"Module: batch={batch}",work)
    elif exercise_id == "losses":
        logits_cases=[([[2.,-1.],[-2.,3.]],[0,1]),([[5.,0.,-2.],[-1.,3.,1.]],[2,1])] if not transfer else [([[0.,0.,0.],[8.,-3.,1.]],[1,0]),([[-100.,100.]],[0])]
        for i,(rows,targets) in enumerate(logits_cases):
            def work(rows=rows,targets=targets):
                pred=torch.tensor(rows,requires_grad=True); target=torch.tensor(targets)
                expected=torch.nn.functional.cross_entropy(pred,target)
                actual=function("loss_for")("classification",pred,target)
                tensor_close(actual,expected,"Cross-entropy отличается: передавайте raw logits")
                ag=torch.autograd.grad(actual,pred,retain_graph=True)[0]
                eg=torch.autograd.grad(expected,pred)[0]; tensor_close(ag,eg,"Неверный gradient loss")
            check(f"Logits → cross-entropy {i+1}",work)
        def regression():
            pred=torch.tensor([1.,-2.,3.] if not transfer else [-4.,0.,7.],requires_grad=True); target=torch.tensor([2.,0.,1.])
            actual=function("loss_for")("regression",pred,target)
            tensor_close(actual,torch.nn.functional.mse_loss(pred,target),"Ожидалась MEAN squared error")
            require(actual.requires_grad,"Loss должна сохранять gradient")
        check("Regression MSE",regression)
        def unknown():
            try: function("loss_for")("unknown",torch.zeros(1),torch.zeros(1))
            except ValueError: return
            raise AssertionError("Неизвестный kind должен вызывать ValueError")
        check("Неизвестная задача",unknown)
    elif exercise_id == "optimizer":
        for i,(w,b,lr) in enumerate(([(0.,0.,.1),(.5,-1.,.03)] if not transfer else [(-.5,2.,.02),(1.,0.,.04)])):
            def work(w=w,b=b,lr=lr):
                model=torch.nn.Linear(1,1); model.eval()
                with torch.no_grad(): model.weight.fill_(w); model.bias.fill_(b)
                model.weight.grad=torch.full_like(model.weight,13); model.bias.grad=torch.full_like(model.bias,-9)
                x=torch.tensor([[-1.],[1.],[2.]]); y=2*x+1
                error=w*x+b-y; expected_loss=(error**2).mean().item()
                expected_w=w-lr*(2*(error*x).mean().item()); expected_b=b-lr*(2*error.mean().item())
                opt=torch.optim.SGD(model.parameters(),lr=lr)
                actual=function("train_step")(model,x,y,opt)
                close(actual,expected_loss,"Возвращайте loss до step")
                close(model.weight.item(),expected_w,"Weight после шага: проверьте zero_grad/backward/step")
                close(model.bias.item(),expected_b,"Bias после шага")
                require(model.training,"model.train() должен быть вызван")
            check(f"SGD и старые gradients {i+1}",work)
    elif exercise_id == "modes":
        def dropout():
            model=torch.nn.Sequential(torch.nn.Linear(2,2),torch.nn.Dropout(.9))
            with torch.no_grad(): model[0].weight.copy_(torch.eye(2)); model[0].bias.zero_()
            model.train(); x=torch.tensor([[2.,3.],[-1.,4.]] if not transfer else [[7.,1.],[2.,-6.]],requires_grad=True)
            actual=function("predict")(model,x)
            tensor_close(actual,x.detach(),"Dropout всё ещё активен; вызовите eval")
            require(not actual.requires_grad,"Не отключена запись graph: нужен torch.no_grad()")
            require(not model.training,"После predict модель должна быть в eval")
        check("Dropout выключен, graph не записан",dropout)
        def batchnorm():
            model=torch.nn.BatchNorm1d(2); model.train()
            with torch.no_grad(): model.running_mean.copy_(torch.tensor([1.,-2.])); model.running_var.copy_(torch.tensor([4.,9.]))
            x=torch.tensor([[3.,1.]],requires_grad=True)
            expected=(x.detach()-model.running_mean)/torch.sqrt(model.running_var+model.eps)
            actual=function("predict")(model,x)
            tensor_close(actual,expected,"В eval BatchNorm использует running statistics")
            require(not actual.requires_grad,"Нужен no_grad, а не только eval")
        check("BatchNorm: один объект в eval",batchnorm)
    elif exercise_id == "training":
        def fitting():
            slope,bias=(-1.5,.7) if transfer else (2.,1.)
            x=torch.tensor([[-2.],[-1.],[0.],[1.],[2.]])
            xv=torch.tensor([[-1.5],[.5],[1.5]])
            y=slope*x+bias; yv=slope*xv+bias
            result=function("fit_line")(x.clone(),y.clone(),xv.clone(),yv.clone())
            require(isinstance(result,dict),"Верните dict model/train_loss/val_loss")
            model=result.get("model"); require(isinstance(model,torch.nn.Module),"model должен быть nn.Module")
            with torch.no_grad():
                train_loss=torch.nn.functional.mse_loss(model(x),y).item(); val_loss=torch.nn.functional.mse_loss(model(xv),yv).item()
            close(result.get("train_loss"),train_loss,"train_loss не соответствует модели")
            close(result.get("val_loss"),val_loss,"val_loss не соответствует отложенным данным")
            require(train_loss<.02 and val_loss<.03,f"Модель ещё не выучила простую прямую: train={train_loss:.4f}, validation={val_loss:.4f}")
        check("Обучение и честные метрики",fitting)
        def leakage():
            x=torch.tensor([[-2.],[-1.],[0.],[1.],[2.]])
            xv=torch.tensor([[-1.5],[.5]])
            a=function("fit_line")(x.clone(),3*x-.5,xv.clone(),3*xv-.5)
            b=function("fit_line")(x.clone(),3*x-.5,xv.clone(),3*xv+30)
            with torch.no_grad(): pa=a["model"](x); pb=b["model"](x)
            tensor_close(pa,pb,"Изменение validation labels изменило обученную модель: возможен leakage или не сброшен seed",atol=1e-4)
            require(b["val_loss"]>100,"Validation loss должна отразить неверные validation labels")
        check("Validation не участвует в обучении",leakage)
    elif exercise_id == "normalization":
        cases=[[[1.,2.,3.],[10.,20.,30.]],[[5.,5.,5.]],[[1.,-1.,2.,-2.]]] if not transfer else [[[4.,8.],[-2.,7.],[3.,3.]],[[100.,101.,103.]]]
        for i,rows in enumerate(cases):
            def work(rows=rows):
                x=torch.tensor(rows,requires_grad=True)
                actual=function("normalize_rows")(x)
                expected=torch.nn.functional.layer_norm(x,(x.shape[-1],),eps=1e-5)
                tensor_close(actual,expected,"Неверная ось, variance или eps")
                require(actual.requires_grad,"Нормализация должна сохранять graph")
            check(f"LayerNorm, случай {i+1}",work)
        def independent():
            row=torch.tensor([[1.,3.,8.]])
            a=function("normalize_rows")(row); b=function("normalize_rows")(torch.cat([row,torch.tensor([[100.,-100.,0.]])]))
            tensor_close(a,b[:1],"Результат строки зависит от соседей: это не LayerNorm по последней оси")
        check("Независимость от соседей по batch",independent)
        def architecture():
            for p in (0., .2, .8):
                model=function("build_dropout_model")(p)
                require(isinstance(model,torch.nn.Sequential),"Верните nn.Sequential из четырёх описанных слоёв")
                layers=list(model.children())
                require(len(layers)==4 and isinstance(layers[0],torch.nn.Linear) and isinstance(layers[1],torch.nn.ReLU)
                        and isinstance(layers[2],torch.nn.Dropout) and isinstance(layers[3],torch.nn.Linear),
                        "Порядок: Linear(2,16), ReLU(), Dropout(p), Linear(16,1)")
                require((layers[0].in_features,layers[0].out_features,layers[3].in_features,layers[3].out_features)==(2,16,16,1),
                        "Размеры слоёв должны образовать маршрут [batch,2] → [batch,16] → [batch,1]")
                close(layers[2].p,p,"В слой Dropout передан не тот p")
                model.eval(); x=torch.tensor([[.3,-.7],[.2,.9]],requires_grad=True)
                prediction=model(x)
                require(tuple(prediction.shape)==(2,1),"Модель должна возвращать [batch,1]")
                prediction.sum().backward()
                require(all(parameter.grad is not None for parameter in model.parameters()),"Все параметры должны участвовать в graph")
        check("Три вероятности и связанная архитектура",architecture)
        def evaluation():
            class ObserveMode(torch.nn.Module):
                def __init__(self):
                    super().__init__(); self.calls=[]
                def forward(self,x):
                    self.calls.append((self.training,torch.is_grad_enabled()))
                    return x[:,:1]*2+x[:,1:]
            model=ObserveMode(); model.train()
            x=torch.tensor([[1.,2.],[-1.,3.]],requires_grad=True)
            y=torch.tensor([[5.],[0.]])
            actual=function("evaluate_mse")(model,x,y)
            close(actual,1.,"evaluate_mse должна усреднять квадраты ошибок")
            require(model.calls and all(not training and not gradients for training,gradients in model.calls),
                    "При проверке нужны model.eval() и torch.no_grad(); это отдельные операции")
            require(not model.training,"Оставьте model в eval после evaluate_mse")
        check("Реальный вызов оценки в eval без graph",evaluation)
        if all(result["passed"] for result in results):
            def experiment():
                nonlocal artifact
                artifact=_dropout_experiment(namespace,transfer)
            check("Обучение трёх сетей и измеренные кривые",experiment)
    elif exercise_id == "two_sum":
        cases=[([2,7,11,15],9),([3,3],6),([],0),([1,2],8)] if not transfer else [([-2,4,1,8],6),([0,0,1],0),([3],6),([4,1,9,3],12)]
        for i,(nums,target) in enumerate(cases):
            def work(nums=nums,target=target):
                original=nums[:]; actual=function("two_sum")(nums,target)
                require(nums==original,"Не меняйте входной список")
                exists=any(nums[a]+nums[b]==target for a in range(len(nums)) for b in range(a+1,len(nums)))
                if not exists: require(actual==[],"Пары нет: верните []"); return
                require(isinstance(actual,(list,tuple)) and len(actual)==2,"Верните два индекса")
                a,b=actual; require(isinstance(a,int) and isinstance(b,int) and 0<=a<len(nums) and 0<=b<len(nums) and a!=b,"Нужны разные допустимые индексы")
                require(nums[a]+nums[b]==target,"Выбранная пара не даёт target")
            check(f"Hash map, случай {i+1}",work)
    elif exercise_id == "agent_loop":
        cases=[(0,3,5,False),(5,1,2,False),(2,2,7,False),(0,2,3,True)] if not transfer else [(3,-1,8,False),(-3,2,0,False),(1,9,2,True)]
        for i,(start,target,budget,stuck) in enumerate(cases):
            def work(start=start,target=target,budget=budget,stuck=stuck):
                calls=[]; position=start
                def tool(name,args):
                    nonlocal position
                    require(len(calls)<budget,"Превышен budget tool calls")
                    require(name=="step" and isinstance(args,dict),"Неверный tool name/schema")
                    require(args.get("position")==position,"Игнорируется результат прошлого tool call")
                    require(args.get("delta")==(1 if target>position else -1),"Неверное направление")
                    calls.append(args.copy())
                    if not stuck: position+=args["delta"]
                    return {"position":position}
                actual=function("navigate")(tool,start,target,budget)
                expected_calls=0 if start==target else budget if stuck else min(abs(target-start),budget)
                require(len(calls)==expected_calls,"Неверное число реальных tool calls")
                require(actual=={"position":position,"calls":len(calls),"reason":"goal" if position==target else "budget"},"Ответ не соответствует реальным вызовам и stop condition")
            check(f"Tool loop, случай {i+1}",work)
    elif exercise_id == "brackets":
        cases=[("{a:[()]}",True),("([)]",False),("",True),("]",False),("((",False)] if not transfer else [("x{[]}(y)",True),("(()))",False),("[({})]",True),("text",True),("{[}",False)]
        for i,(value,expected) in enumerate(cases):
            def work(value=value,expected=expected): require(function("balanced")(value) is expected,"Неверная вложенность или оставшийся stack")
            check(f"Stack, случай {i+1}",work)
    elif exercise_id == "longest_unique":
        cases=[("abcabcbb",3),("bbbbb",1),("",0),("abba",2),("pwwkew",3)] if not transfer else [("dvdf",3),("караван",3),("abcdef",6),("tmmzuxt",5),(" ",1)]
        for i,(value,expected) in enumerate(cases):
            check(f"Sliding window, случай {i+1}",lambda value=value,expected=expected:close(function("longest_unique")(value),expected,"Длина уникального фрагмента"))
    elif exercise_id == "split":
        cases=[([{"id":"a","group":"x"},{"id":"b","group":"y"},{"id":"c","group":"x"},{"id":"d","group":"z"}],{"y"},{"z"}),([],set(),set())] if not transfer else [([{"id":"a","group":1},{"id":"b","group":2},{"id":"c","group":1}],{1},set()),([{"id":"a","group":"z"}],set(),{"z"})]
        for i,(rows,vg,tg) in enumerate(cases):
            def work(rows=rows,vg=vg,tg=tg):
                import copy
                original=copy.deepcopy(rows); actual=function("split_groups")(rows,vg,tg)
                expected={key:[row for row in rows if ("test" if row["group"] in tg else "validation" if row["group"] in vg else "train")==key] for key in ["train","validation","test"]}
                require(actual==expected,"Группа распределена неверно или потерян порядок")
                require(rows==original,"Входные данные изменены")
            check(f"Group split {i+1}",work)
        def overlap():
            try: function("split_groups")([],{"x"},{"x"})
            except ValueError:return
            raise AssertionError("Пересекающиеся группы нужно отвергнуть")
        check("Запрет пересечения",overlap)
    elif exercise_id == "retrieval":
        docs=[{"id":"b","text":"синий фонарь фонарь"},{"id":"a","text":"синий мост"},{"id":"c","text":"красный фонарь"}]
        cases=[("синий фонарь",2,["b","a"]),("неизвестно",3,[]),("синий",0,[])] if not transfer else [("ФОНАРЬ",5,["b","c"]),("мост",1,["a"]),("",2,[])]
        for i,(query,k,expected) in enumerate(cases):
            def work(query=query,k=k,expected=expected):require(function("retrieve")(query,docs,k)==expected,"Неверный score, tie-break по id или top-k")
            check(f"Retrieval {i+1}",work)
    elif exercise_id == "attention":
        for n,d,v in ([(2,2,2),(3,4,1)] if not transfer else [(4,3,2),(1,5,3)]):
            def work(n=n,d=d,v=v):
                q=torch.linspace(-1,1,d,requires_grad=True); keys=torch.arange(n*d,dtype=torch.float32).reshape(n,d)/5
                values=torch.arange(n*v,dtype=torch.float32).reshape(n,v)+.2
                expected=torch.softmax((keys@q)/math.sqrt(d),dim=0)@values
                actual=function("attend")(q,keys,values)
                tensor_close(actual,expected,"Проверьте sqrt(d), softmax по токенам и смешивание V")
                require(actual.requires_grad,"Attention должна сохранять graph")
            check(f"Attention n={n}, d={d}",work)
    elif exercise_id == "gradient_descent":
        cases=[(0.,[1.,2.],[2.,4.],.1),(2.,[1.,2.],[2.,4.],.3),(7.,[],[],.1)] if not transfer else [(-1.,[-2.,1.],[-4.,2.],.05),(3.,[0.,1.],[1.,1.],0.)]
        for i,(w,xs,ys,lr) in enumerate(cases):
            expected=w-lr*2*sum((w*x-y)*x for x,y in zip(xs,ys))/len(xs) if xs else w
            check(f"Gradient descent {i+1}",lambda w=w,xs=xs,ys=ys,lr=lr,expected=expected:close(function("descend")(w,xs,ys,lr),expected,"Новый weight"))

    passed=bool(results) and all(result["passed"] for result in results)
    if passed:
        feedback="Проверки вычислений пройдены на новых входных данных. Объясните результат своими словами; автоматическая проверка кода не оценивает свободный ответ."
    else:
        failed=next((r for r in results if not r["passed"]),None)
        feedback=(failed["detail"] if failed else "Проверки не найдены.") + " Подсказка: " + EXERCISES[exercise_id]["hint"]
    response={"passed":passed,"feedback":feedback,"results":results}
    if artifact is not None:
        response["artifact"]=artifact
    return response
