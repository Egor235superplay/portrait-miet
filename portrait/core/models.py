"""Модели данных модуля «Портрет личности».

Здесь описаны структуры, которыми обмениваются части модуля:

    Question     — вопрос методики;
    Answer       — ответ пользователя на вопрос;
    ScaleScore   — балл по одной шкале методики;
    MethodResult — результат одной методики;
    Portrait     — итоговый отчёт «Портрет личности» по всем методикам.

Каждую модель можно перевести в словарь (to_dict) и обратно (from_dict),
чтобы сохранять и читать её в формате JSON.

Модели сами проверяют свои данные при создании и при ошибке
выбрасывают ValueError с понятным сообщением.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class QuestionType(StrEnum):
    """Тип вопроса — определяет, какой ответ на него допустим."""

    CHOICE = "choice"  # выбор одного варианта из списка
    SCALE = "scale"    # оценка по шкале (например, от 1 до 5); значения шкалы задаются в options
    NUMBER = "number"  # ответ числом (например, в задачах на когнитивную рефлексию)
    TEXT = "text"      # свободный ответ строкой


class Status(StrEnum):
    """Статус результата методики."""

    OK = "ok"            # все вопросы отвечены, результат посчитан
    PARTIAL = "partial"  # часть вопросов пропущена, результат посчитан с оговоркой
    ERROR = "error"      # методика упала или вернула результат в неверном формате
    NO_DATA = "no_data"  # результата нет: слишком много пропусков или методика ничего не прислала


def _is_number(value: object) -> bool:
    """Проверяет, что значение — число (bool числом не считаем)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# Вопросы и ответы
# ---------------------------------------------------------------------------


@dataclass
class Option:
    """Вариант ответа на вопрос.

    value — что сохраняется как ответ (например, 1..5 или "а");
    label — что видит пользователь (например, «Скорее согласен»).
    """

    value: int | str
    label: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, str)) or isinstance(self.value, bool):
            raise ValueError(f"Значение варианта должно быть числом или строкой, получено: {self.value!r}")
        if not self.label.strip():
            raise ValueError(f"У варианта {self.value!r} пустая подпись")

    def to_dict(self) -> dict:
        return {"value": self.value, "label": self.label}

    @classmethod
    def from_dict(cls, data: dict) -> Option:
        return cls(value=data["value"], label=data["label"])


@dataclass
class Question:
    """Вопрос методики.

    id        — уникальный id вида "<id методики>_q<номер>", например "m01_q05";
    method_id — id методики, к которой относится вопрос, например "m01";
    text      — текст вопроса;
    order     — порядковый номер внутри методики, начиная с 1;
    type      — тип вопроса (см. QuestionType);
    options   — варианты ответа; нужны для CHOICE и SCALE, для NUMBER и TEXT — пусто.
    """

    id: str
    method_id: str
    text: str
    order: int
    type: QuestionType = QuestionType.CHOICE
    options: list[Option] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Тип может прийти строкой (например, из JSON) — приводим к QuestionType.
        self.type = QuestionType(self.type)

        if not self.method_id:
            raise ValueError("У вопроса не указан method_id")
        if not self.id.startswith(self.method_id + "_"):
            raise ValueError(f"id вопроса {self.id!r} должен начинаться с {self.method_id + '_'!r}")
        if not self.text.strip():
            raise ValueError(f"Вопрос {self.id}: пустой текст")
        if self.order < 1:
            raise ValueError(f"Вопрос {self.id}: order должен быть не меньше 1")

        if self.type in (QuestionType.CHOICE, QuestionType.SCALE):
            if not self.options:
                raise ValueError(f"Вопрос {self.id}: для типа {self.type} нужны варианты ответа")
            values = [option.value for option in self.options]
            if len(values) != len(set(values)):
                raise ValueError(f"Вопрос {self.id}: значения вариантов ответа повторяются")
        elif self.options:
            raise ValueError(f"Вопрос {self.id}: у типа {self.type} не бывает вариантов ответа")

    def is_valid_value(self, value: object) -> bool:
        """Проверяет, подходит ли значение как ответ на этот вопрос."""
        if self.type in (QuestionType.CHOICE, QuestionType.SCALE):
            if isinstance(value, bool):
                return False
            return value in [option.value for option in self.options]
        if self.type == QuestionType.NUMBER:
            return _is_number(value)
        # QuestionType.TEXT
        return isinstance(value, str) and bool(value.strip())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "method_id": self.method_id,
            "text": self.text,
            "order": self.order,
            "type": str(self.type),
            "options": [option.to_dict() for option in self.options],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Question:
        return cls(
            id=data["id"],
            method_id=data["method_id"],
            text=data["text"],
            order=data["order"],
            type=data.get("type", QuestionType.CHOICE),
            options=[Option.from_dict(item) for item in data.get("options", [])],
        )


@dataclass
class Answer:
    """Ответ пользователя на вопрос.

    Если пользователь ответил — value заполнено, skipped=False.
    Если пользователь отказался отвечать — value=None, skipped=True
    (для этого удобно использовать Answer.skip(question_id)).
    """

    question_id: str
    value: int | float | str | None = None
    skipped: bool = False

    def __post_init__(self) -> None:
        if self.skipped and self.value is not None:
            raise ValueError(f"Ответ на {self.question_id}: у пропущенного вопроса не может быть значения")
        if not self.skipped and self.value is None:
            raise ValueError(f"Ответ на {self.question_id}: нет значения (для пропуска используйте Answer.skip)")

    @classmethod
    def skip(cls, question_id: str) -> Answer:
        """Создаёт ответ «пользователь пропустил вопрос»."""
        return cls(question_id=question_id, skipped=True)

    def to_dict(self) -> dict:
        return {"question_id": self.question_id, "value": self.value, "skipped": self.skipped}

    @classmethod
    def from_dict(cls, data: dict) -> Answer:
        return cls(
            question_id=data["question_id"],
            value=data.get("value"),
            skipped=data.get("skipped", False),
        )


# Ответы по одной методике: id вопроса -> ответ.
# None означает, что пользователь до вопроса не дошёл (например, остановил опрос на середине).
MethodAnswers = dict[str, Answer | None]


# ---------------------------------------------------------------------------
# Результаты
# ---------------------------------------------------------------------------


@dataclass
class ScaleScore:
    """Балл по одной шкале методики.

    scale — название шкалы (например, «Экстраверсия»);
    raw   — сырой балл, посчитанный по ключу;
    level — уровень: «низкий», «средний», «высокий» или категория; None, если уровни не предусмотрены.
    """

    scale: str
    raw: int | float
    level: str | None = None

    def __post_init__(self) -> None:
        if not self.scale.strip():
            raise ValueError("У шкалы пустое название")
        if not _is_number(self.raw):
            raise ValueError(f"Шкала {self.scale!r}: балл должен быть числом, получено: {self.raw!r}")

    def to_dict(self) -> dict:
        return {"scale": self.scale, "raw": self.raw, "level": self.level}

    @classmethod
    def from_dict(cls, data: dict) -> ScaleScore:
        return cls(scale=data["scale"], raw=data["raw"], level=data.get("level"))


@dataclass
class MethodResult:
    """Результат одной методики.

    method_id, method_name — какая методика;
    status         — статус результата (см. Status);
    scores         — баллы по шкалам; обязательны для статусов OK и PARTIAL;
    interpretation — текстовый вывод для пользователя;
    answered       — сколько вопросов отвечено;
    total          — сколько вопросов в методике;
    errors         — описания проблем (для статусов ERROR и NO_DATA — причина).
    """

    method_id: str
    method_name: str
    status: Status
    scores: list[ScaleScore] = field(default_factory=list)
    interpretation: str = ""
    answered: int = 0
    total: int = 0
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Статус может прийти строкой (например, из JSON) — приводим к Status.
        self.status = Status(self.status)

        if not self.method_id:
            raise ValueError("У результата не указан method_id")
        if self.answered < 0 or self.total < 0:
            raise ValueError(f"Результат {self.method_id}: answered и total не могут быть отрицательными")
        if self.answered > self.total:
            raise ValueError(f"Результат {self.method_id}: отвечено ({self.answered}) больше, чем вопросов ({self.total})")
        if self.status in (Status.OK, Status.PARTIAL) and not self.scores:
            raise ValueError(f"Результат {self.method_id}: при статусе {self.status} нужны баллы (scores)")

    @classmethod
    def error(cls, method_id: str, method_name: str, message: str, total: int = 0) -> MethodResult:
        """Создаёт результат «методика завершилась с ошибкой»."""
        return cls(method_id=method_id, method_name=method_name, status=Status.ERROR,
                   total=total, errors=[message])

    @classmethod
    def no_data(cls, method_id: str, method_name: str, reason: str, total: int = 0) -> MethodResult:
        """Создаёт результат «данных для расчёта нет»."""
        return cls(method_id=method_id, method_name=method_name, status=Status.NO_DATA,
                   total=total, errors=[reason])

    def to_dict(self) -> dict:
        return {
            "method_id": self.method_id,
            "method_name": self.method_name,
            "status": str(self.status),
            "scores": [score.to_dict() for score in self.scores],
            "interpretation": self.interpretation,
            "answered": self.answered,
            "total": self.total,
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: dict) -> MethodResult:
        return cls(
            method_id=data["method_id"],
            method_name=data["method_name"],
            status=data["status"],
            scores=[ScaleScore.from_dict(item) for item in data.get("scores", [])],
            interpretation=data.get("interpretation", ""),
            answered=data.get("answered", 0),
            total=data.get("total", 0),
            errors=list(data.get("errors", [])),
        )


@dataclass
class Portrait:
    """Итоговый отчёт «Портрет личности».

    respondent_id — анонимный id того, кто проходил опрос;
    results       — результаты методик в порядке прохождения;
    warnings      — предупреждения сборщика (дубли, неверный формат и т. п.);
    created_at    — дата и время формирования отчёта (ISO, до секунд).
    """

    respondent_id: str
    results: list[MethodResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def get(self, method_id: str) -> MethodResult | None:
        """Возвращает результат методики по id или None, если его нет."""
        for result in self.results:
            if result.method_id == method_id:
                return result
        return None

    def summary(self) -> dict[str, int]:
        """Считает, сколько методик в каждом статусе: {"ok": 15, "partial": 3, ...}."""
        counts = {str(status): 0 for status in Status}
        for result in self.results:
            counts[str(result.status)] += 1
        return counts

    def to_dict(self) -> dict:
        return {
            "respondent_id": self.respondent_id,
            "created_at": self.created_at,
            "summary": self.summary(),  # только для чтения человеком; при загрузке пересчитывается
            "results": [result.to_dict() for result in self.results],
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Portrait:
        return cls(
            respondent_id=data["respondent_id"],
            results=[MethodResult.from_dict(item) for item in data.get("results", [])],
            warnings=list(data.get("warnings", [])),
            created_at=data["created_at"],
        )

    def to_json(self) -> str:
        """Переводит отчёт в JSON-строку (кириллица сохраняется как есть)."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> Portrait:
        """Читает отчёт из JSON-строки."""
        return cls.from_dict(json.loads(text))
