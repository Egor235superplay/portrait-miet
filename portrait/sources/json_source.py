from pathlib import Path  # Для работы с путями к файлам
import json               # Для чтения JSON-файлов

# Импортируем наш класс-методику из соседней папки methods
from ..methods.json_method import JsonMethod  

# И импортируем контракт от главного разработчика
from .base import QuestionSource


class JsonSource(QuestionSource):
    """
    Загрузчик методик из файлов.
    
    Движок вызывает только метод load_methods() и получает готовые объекты методик.
    Откуда они взялись — движку не важно.
    """

    def __init__(self, methods_folder: str = "methods/data"):
        # При создании мы запоминаем путь до папки с файлами.
        self.folder_path = Path(methods_folder)  # Преобразуем строку в объект пути

    def load_methods(self) -> list[JsonMethod]:
        result = []
        
        # Проходимся по всем файлам в папке
        for file_path in self.folder_path.glob("*.json"): 
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)  # Считываем сырой словарь из файла
                
                # Создаём экземпляр нашей методики!
                method = JsonMethod(data)
                result.append(method)
            
            except Exception as e:
                raise ValueError(
                    f"Ошибка при чтении {file_path.name}: {e}"
                ) from None

        # Методики должны возвращаться строго в том порядке, как в справочнике METHODS
        sorted_result = sorted(result, key=lambda x: x.method_id)

        return sorted_result