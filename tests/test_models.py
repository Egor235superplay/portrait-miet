"""Тесты моделей данных (portrait/core/models.py)."""

import unittest

from portrait.core.models import (
    Answer,
    MethodResult,
    Option,
    Portrait,
    Question,
    QuestionType,
    ScaleScore,
    Status,
)


def make_scale_question(question_id: str = "m01_q01") -> Question:
    """Вопрос со шкалой от 1 до 3 для тестов."""
    return Question(
        id=question_id,
        method_id="m01",
        text="Мне нравится узнавать новое",
        order=1,
        type=QuestionType.SCALE,
        options=[Option(1, "Не согласен"), Option(2, "Затрудняюсь"), Option(3, "Согласен")],
    )


class QuestionTests(unittest.TestCase):

    def test_valid_question_is_created(self):
        question = make_scale_question()
        self.assertEqual(question.type, QuestionType.SCALE)
        self.assertEqual(len(question.options), 3)

    def test_type_from_string(self):
        question = Question(id="m04_q01", method_id="m04", text="Сколько?", order=1, type="number")
        self.assertEqual(question.type, QuestionType.NUMBER)

    def test_unknown_type_is_rejected(self):
        with self.assertRaises(ValueError):
            Question(id="m01_q01", method_id="m01", text="Текст", order=1, type="slider")

    def test_id_must_start_with_method_id(self):
        with self.assertRaises(ValueError):
            Question(id="q01", method_id="m01", text="Текст", order=1, type="text")

    def test_empty_text_is_rejected(self):
        with self.assertRaises(ValueError):
            Question(id="m01_q01", method_id="m01", text="   ", order=1, type="text")

    def test_order_starts_from_one(self):
        with self.assertRaises(ValueError):
            Question(id="m01_q01", method_id="m01", text="Текст", order=0, type="text")

    def test_choice_without_options_is_rejected(self):
        with self.assertRaises(ValueError):
            Question(id="m01_q01", method_id="m01", text="Текст", order=1, type="choice")

    def test_duplicate_option_values_are_rejected(self):
        with self.assertRaises(ValueError):
            Question(id="m01_q01", method_id="m01", text="Текст", order=1,
                     options=[Option(1, "Да"), Option(1, "Нет")])

    def test_number_with_options_is_rejected(self):
        with self.assertRaises(ValueError):
            Question(id="m04_q01", method_id="m04", text="Сколько?", order=1,
                     type="number", options=[Option(1, "Один")])

    def test_is_valid_value_for_scale(self):
        question = make_scale_question()
        self.assertTrue(question.is_valid_value(2))
        self.assertFalse(question.is_valid_value(4))
        self.assertFalse(question.is_valid_value("2"))
        self.assertFalse(question.is_valid_value(True))  # True == 1, но это не ответ

    def test_is_valid_value_for_number(self):
        question = Question(id="m04_q01", method_id="m04", text="Сколько?", order=1, type="number")
        self.assertTrue(question.is_valid_value(5))
        self.assertTrue(question.is_valid_value(0.5))
        self.assertFalse(question.is_valid_value("5"))
        self.assertFalse(question.is_valid_value(False))

    def test_is_valid_value_for_text(self):
        question = Question(id="m05_q01", method_id="m05", text="Опишите", order=1, type="text")
        self.assertTrue(question.is_valid_value("ответ"))
        self.assertFalse(question.is_valid_value("   "))
        self.assertFalse(question.is_valid_value(5))

    def test_dict_round_trip(self):
        question = make_scale_question()
        self.assertEqual(Question.from_dict(question.to_dict()), question)


class AnswerTests(unittest.TestCase):

    def test_answer_with_value(self):
        answer = Answer("m01_q01", 3)
        self.assertFalse(answer.skipped)

    def test_skip(self):
        answer = Answer.skip("m01_q01")
        self.assertTrue(answer.skipped)
        self.assertIsNone(answer.value)

    def test_answer_without_value_is_rejected(self):
        with self.assertRaises(ValueError):
            Answer("m01_q01")

    def test_skipped_answer_with_value_is_rejected(self):
        with self.assertRaises(ValueError):
            Answer("m01_q01", 3, skipped=True)

    def test_dict_round_trip(self):
        for answer in (Answer("m01_q01", 3), Answer.skip("m01_q02")):
            self.assertEqual(Answer.from_dict(answer.to_dict()), answer)


class MethodResultTests(unittest.TestCase):

    def test_ok_requires_scores(self):
        with self.assertRaises(ValueError):
            MethodResult("m01", "Методика", Status.OK, answered=3, total=3)

    def test_answered_cannot_exceed_total(self):
        with self.assertRaises(ValueError):
            MethodResult("m01", "Методика", Status.OK, scores=[ScaleScore("Шкала", 5)],
                         answered=4, total=3)

    def test_score_must_be_number(self):
        with self.assertRaises(ValueError):
            ScaleScore("Шкала", "5")

    def test_error_factory(self):
        result = MethodResult.error("m01", "Методика", "Деление на ноль", total=10)
        self.assertEqual(result.status, Status.ERROR)
        self.assertEqual(result.errors, ["Деление на ноль"])
        self.assertEqual(result.total, 10)

    def test_no_data_factory(self):
        result = MethodResult.no_data("m01", "Методика", "Нет ответов")
        self.assertEqual(result.status, Status.NO_DATA)
        self.assertEqual(result.scores, [])

    def test_status_from_string(self):
        result = MethodResult("m01", "Методика", "no_data")
        self.assertEqual(result.status, Status.NO_DATA)


class PortraitTests(unittest.TestCase):

    def make_portrait(self) -> Portrait:
        return Portrait(
            respondent_id="anon-001",
            results=[
                MethodResult("m01", "Оценка особенностей личности", Status.OK,
                             scores=[ScaleScore("Экстраверсия", 14, "высокий")],
                             interpretation="Общительный", answered=3, total=3),
                MethodResult("m02", "Индекс устойчивости идентичности", Status.PARTIAL,
                             scores=[ScaleScore("Индекс", 7.5, "средний")], answered=2, total=3),
                MethodResult.error("m03", "Критическое мышление", "Сбой подсчёта", total=5),
                MethodResult.no_data("m04", "Когнитивная рефлексия", "Нет результата"),
            ],
            warnings=["Пример предупреждения"],
        )

    def test_summary(self):
        self.assertEqual(self.make_portrait().summary(),
                         {"ok": 1, "partial": 1, "error": 1, "no_data": 1})

    def test_get(self):
        portrait = self.make_portrait()
        self.assertEqual(portrait.get("m02").status, Status.PARTIAL)
        self.assertIsNone(portrait.get("m20"))

    def test_json_round_trip(self):
        portrait = self.make_portrait()
        text = portrait.to_json()
        self.assertIn("Экстраверсия", text)  # кириллица не экранируется
        self.assertEqual(Portrait.from_json(text), portrait)


if __name__ == "__main__":
    unittest.main()
