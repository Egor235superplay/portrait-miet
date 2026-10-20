"""Методика, описанная в JSON-файле.

Формат файла:

    {
      "method_id": "m01",
      "questions": [
        {"text": "Текст вопроса", "type": "scale",
         "options": [{"value": 1, "label": "Не согласен"}, ...]}
      ]
    }

id вопроса (m01_q01), method_id и order в файле не пишутся —
их проставляет JsonMethod по порядку вопросов.
"""

from portrait.core.contracts import MethodBlock, METHODS
from portrait.core.models import MethodAnswers, MethodResult, Option, Question, ScaleScore, Status


class JsonMethod(MethodBlock):
    def __init__(self, method_data: dict):
        method_id = method_data.get("method_id")
        if method_id not in METHODS:
            raise ValueError(f"method_id {method_id!r} нет в справочнике METHODS")
        if not isinstance(method_data.get("questions"), list) or not method_data["questions"]:
            raise ValueError("нет поля questions или список вопросов пуст")

        self.id = method_id
        self.name = METHODS[method_id]
        self.method_data = method_data
        # Вопросы собираем сразу: ошибка в файле видна при загрузке, а не посреди опроса
        self.questions = [
            self._make_question(number, question_dict)
            for number, question_dict in enumerate(method_data["questions"], start=1)
        ]

    def _make_question(self, number: int, question_dict: dict) -> Question:
        # id, method_id и order проставляем сами по порядку вопросов
        try:
            return Question(
                id=f"{self.id}_q{number:02d}",
                method_id=self.id,
                text=question_dict["text"],
                order=number,
                type=question_dict.get("type", "scale"),  # По умолчанию шкала (если типа нет)
                options=[Option.from_dict(option) for option in question_dict.get("options", [])],
            )
        except KeyError as error:
            raise ValueError(f"вопрос {number}: нет поля {error}") from error

    def get_questions(self) -> list[Question]:
        # Отдаём копию, чтобы движок случайно не изменил список вопросов методики
        return list(self.questions)

    def process(self, answers: MethodAnswers) -> MethodResult:
        total = len(self.questions)
        # Отвеченные — те, где ответ есть и он не пропущен.
        # None (не дошёл до вопроса) и Answer.skip (отказался отвечать) не считаются.
        answered = [
            answer for answer in (answers.get(question.id) for question in self.questions)
            if answer is not None and not answer.skipped
        ]

        if not answered:
            return MethodResult.no_data(self.id, self.name, "Нет ни одного ответа", total=total)

        # Временный подсчёт до шага 10: сумма числовых ответов
        total_score = sum(
            answer.value for answer in answered
            if isinstance(answer.value, (int, float)) and not isinstance(answer.value, bool)
        )

        return MethodResult(
            method_id=self.id,
            method_name=self.name,
            status=Status.OK if len(answered) == total else Status.PARTIAL,  # PARTIAL — есть пропуски
            scores=[ScaleScore(scale='Сумма баллов', raw=total_score)],
            interpretation=f"Вы набрали {total_score} баллов",
            answered=len(answered),
            total=total,
        )
