import re
from nbclient.exceptions import CellExecutionError


def grade_notebook(client, submission, tutor_notebook):
    total_points = 0
    # Выполняем каждую ячейку отдельно
    with client.setup_kernel() as kernel:
        for index, cell in enumerate(submission.cells):
            if cell.cell_type == 'code':  # Проверяем, что это кодовая ячейка
                try:
                    client.execute_cell(cell, cell_index=index, store_history=True)
                except CellExecutionError:
                    pass
                if cell.cell_type == 'code':
                    if "# Tests " in cell.source and " points." in cell.source:
                        points = 0
                        match = re.search(r"# Tests (\d+) points", cell.source)
                        if match:
                            points = int(match.group(1))

                        # Замена на соответствующую ячейку из преподавательского файла
                        teacher_cell = tutor_notebook.cells[index]
                        cell.source = teacher_cell.source
                        
                        try:
                            client.execute_cell(cell, index)
                            total_points += points
                        except CellExecutionError as ce:
                            pass
    return total_points
