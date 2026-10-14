"""Точка входа модуля «Портрет личности».

Сейчас выводит список методик из справочника.
Прохождение опроса появится после реализации движка (шаг 4 плана).
"""

from portrait.core.contracts import METHODS


def main() -> None:
    print("Портрет личности — прототип в разработке")
    print(f"Методик в справочнике: {len(METHODS)}")
    for method_id, name in METHODS.items():
        print(f"  {method_id}  {name}")


if __name__ == "__main__":
    main()
