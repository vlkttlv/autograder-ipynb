import re
from app.exceptions import (
    NotFoundSolutionsInAssignmentException,
    NotFoundTestsInAssignmentException,
)


def check_notebook(notebook):
    """Проверка блокнота"""

    # Переменные для отслеживания наличия нужных строк
    solution_found = True
    tests_found = True
    count_test = 0

    for cell in notebook.cells:
        if cell.cell_type == "code":
            # Проверяем наличие строк в коде
            if "def" in cell.source:
                if (
                    "### BEGIN SOLUTION" not in cell.source
                    and "### END SOLUTION" not in cell.source
                ):
                    solution_found = False
                if (
                    "### BEGIN SOLUTION" not in cell.source
                    and "### END SOLUTION" in cell.source
                ):
                    solution_found = False
                if (
                    "### BEGIN SOLUTION" in cell.source
                    and "### END SOLUTION" not in cell.source
                ):
                    solution_found = False

            # Проверка на наличие строк для тестов
            if "# Tests " in cell.source and " points." in cell.source:
                if (
                    "### BEGIN HIDDEN TESTS" not in cell.source
                    and "### END HIDDEN TESTS" not in cell.source
                ):
                    tests_found = False
                if (
                    "### BEGIN HIDDEN TESTS" in cell.source
                    and "### END HIDDEN TESTS" not in cell.source
                ):
                    tests_found = False
                if (
                    "### BEGIN HIDDEN TESTS" not in cell.source
                    and "### END HIDDEN TESTS" in cell.source
                ):
                    tests_found = False
                count_test += 1

    # Проверка, были ли обнаружены нужные блоки
    if not solution_found:
        raise NotFoundSolutionsInAssignmentException
    if not tests_found or count_test == 0:
        raise NotFoundTestsInAssignmentException
    return True


def modify_notebook(notebook):
    """Модификация блокнота, добавление необходимых строчек"""
    for cell in notebook.cells:
        if cell.cell_type == "code":
            source_lines = cell.source.split("\n")
            if (
                "### BEGIN SOLUTION" in cell.source
                and "### END SOLUTION" in cell.source
            ):
                # Поиск индекса начала решения с учетом возможных пробелов
                for i, line in enumerate(source_lines):
                    if "### BEGIN SOLUTION" in line.strip():
                        begin_index = i + 1
                        break
                # Поиск индекса конца решения с учетом возможных пробелов
                for j, line in enumerate(source_lines):
                    if "### END SOLUTION" in line.strip():
                        end_index = j
                        break
                # Проверка, что оба индекса найдены
                if begin_index > 0 and end_index > 0:
                    # Удаляем строки между маркерами
                    source_lines[begin_index - 1 : end_index + 1] = [
                        "### WRITE SOLUTION HERE"
                    ]
                    cell.source = "\n".join(source_lines)

            if (
                "### BEGIN HIDDEN TESTS" in cell.source
                and "### END HIDDEN TESTS" in cell.source
            ):
                begin_index = source_lines.index("### BEGIN HIDDEN TESTS")
                end_index = source_lines.index("### END HIDDEN TESTS") + 1
                # Удаляем строки между маркерами и маркеры
                source_lines[begin_index : end_index + 1] = []
                cell.source = "\n".join(source_lines)

    return notebook


def get_total_points_from_notebook(client, submission):
    total_points = 0
    # Выполняем каждую ячейку отдельно
    with client.setup_kernel() as kernel:
        for index, cell in enumerate(submission.cells):
            if cell.cell_type == "code":  # Проверяем, что это кодовая ячейка
                if "# Tests " in cell.source and " points." in cell.source:
                    points = 0
                    match = re.search(r"# Tests (\d+) points", cell.source)
                    if match:
                        points = int(match.group(1))
                    total_points += points
    return total_points
