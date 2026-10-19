from portrait.core.contracts import MethodBlock, METHODS

class JsonMethod(MethodBlock):
    def __init__(self, method_data: dict):
        self.method_id = method_data["method_id"]
        self.name = METHODS[self.method_id].name
    def get_questions(self) -> list[Question]:
        questions_list = []

        for question_dict in self.method_data['questions']:
            q = Question(
                text=question_dict['text'],
                type=question_dict.get('type', 'scale'), # По умолчанию шкала (если типа нет)
                options=question_dict.get('options')
            )
            questions_list.append(q)

        return questions_list
    def process(self, answers: MethodAnswers) -> MethodResult:
        # Сначала проверим статус
        status = 'ok'
        if len(answers) < len(self.method_data['questions']):
            status = 'partial'  # Есть пропуски
        elif not any(answers.values()):
            status = 'no_data'  # Нет ни одного ответа
        
        total_score = sum(
            answer.value for answer in answers.values()
            if isinstance(answer, Answer) and isinstance(answer.value, int)
        )

        return MethodResult(
            method_id=self.method_id,
            method_name=self.name,
            status=status,
            scores=[ScaleScore(scale='Сумма баллов', raw=total_score)],
            interpretation=f"Вы набрали {total_score} баллов",
            answered=sum(1 for a in answers.values() if a is not None),
            total=len(self.method_data['questions'])
        )