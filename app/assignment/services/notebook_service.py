import nbformat
import re
import logging
from nbclient import NotebookClient
from app.exceptions import (
    NotFoundSolutionsInAssignmentException,
    NotFoundTestsInAssignmentException,
    DecodingIPYNBException,
)
from app.logger import configure_logging

logger = logging.getLogger(__name__)
configure_logging()


class NotebookService:
    @staticmethod
    def read_notebook(content: bytes):
        """
        Преобразует содержимое .ipynb файла из байтов в объект nbformat NotebookNode

        Args:
            content (bytes): Содержимое файла в байтах

        Returns:
            NotebookNode: Загруженный Jupyter Notebook

        Raises:
            DecodingIPYNBException: Если не удалось прочитать или декодировать блокнот
        """
        try:
            return nbformat.reads(content.decode("utf-8"), as_version=4)
        except Exception as e:
            logger.error("Ошибка чтения блокнота: %s", e)
            raise DecodingIPYNBException from e

    @staticmethod
    def check_notebook(notebook):
        """
        Проверяет блокнот на наличие обязательных блоков:
        - Решения между маркерами ### BEGIN SOLUTION / ### END SOLUTION
        - Скрытые тесты между маркерами ### BEGIN HIDDEN TESTS / ### END HIDDEN TESTS

        Args:
            notebook: Загруженный Jupyter Notebook

        Returns:
            bool: True, если блокнот валидный

        Raises:
            NotFoundSolutionsInAssignmentException: Если блоки решения не найдены
            NotFoundTestsInAssignmentException: Если блоки тестов не найдены
        """
        solution_found = True
        tests_found = True
        count_test = 0
        for cell in notebook.cells:
            if cell.cell_type == "code":
                if "def" in cell.source:
                    if (
                        "### BEGIN SOLUTION" not in cell.source
                        or "### END SOLUTION" not in cell.source
                    ):
                        solution_found = False
                if "# Tests " in cell.source and " points." in cell.source:
                    if (
                        "### BEGIN HIDDEN TESTS" not in cell.source
                        or "### END HIDDEN TESTS" not in cell.source
                    ):
                        tests_found = False
                    count_test += 1
        if not solution_found:
            logger.warning("Блоки решения не найдены в блокноте")
            raise NotFoundSolutionsInAssignmentException
        if not tests_found or count_test == 0:
            logger.warning("Блоки тестов не найдены или тестов 0")
            raise NotFoundTestsInAssignmentException
        return True

    @staticmethod
    def modify_notebook(notebook):
        """
        Модифицирует блокнот:
        - Заменяет содержимое блоков решений на '### WRITE SOLUTION HERE'
        - Удаляет скрытые тесты между маркерами

        Args:
            notebook: Загруженный Jupyter Notebook

        Returns:
            NotebookNode: Модифицированный блокнот
        """
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

    @staticmethod
    def get_total_points(notebook):
        """
        Подсчитывает суммарное количество баллов за все тесты в блокноте.

        Args:
            notebook: Загруженный Jupyter Notebook

        Returns:
            int: Общая сумма баллов за все тесты в блокноте
        """
        total = 0
        for cell in notebook.cells:
            if cell.cell_type == "code":
                match = re.search(r"# Tests (\d+) points", cell.source)
                if match:
                    total += int(match.group(1))
        return total
