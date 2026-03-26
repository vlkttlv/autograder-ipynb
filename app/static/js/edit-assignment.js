const resourceFilesInput = document.getElementById('resource_files');
const resourceFilesSelected = document.getElementById('resource-files-selected');

if (resourceFilesInput && resourceFilesSelected) {
  resourceFilesInput.addEventListener('change', () => {
    const selectedNames = Array.from(resourceFilesInput.files).map((file) => file.name);
    resourceFilesSelected.textContent = selectedNames.length
      ? `Выбрано файлов: ${selectedNames.join(', ')}`
      : '';
  });
}

document.querySelectorAll('.resource-delete-btn').forEach((deleteButton) => {
  deleteButton.addEventListener('click', async () => {
    const assignmentId = document.getElementById('assignment-form').dataset.assignmentId;
    const resourceId = deleteButton.dataset.resourceId;

    const shouldDelete = window.confirm('Вы точно хотите удалить файл?');
    if (!shouldDelete) {
      return;
    }

    try {
      const response = await fetch(`/assignments/${assignmentId}/resources/${resourceId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Ошибка удаления дополнительного файла:', errorData);
        document.getElementById('error-message').textContent = errorData.detail || 'Ошибка при удалении дополнительного файла';
        document.getElementById('error-message').classList.remove('hidden');
        return;
      }

      const resourceItem = deleteButton.closest('.resource-item');
      if (resourceItem) {
        const resourceLink = resourceItem.querySelector('a');
        if (resourceLink) {
          resourceLink.classList.add('line-through', 'text-gray-400', 'pointer-events-none');
          resourceLink.removeAttribute('href');
          resourceLink.removeAttribute('download');
        }

        deleteButton.textContent = 'Удалено';
        deleteButton.classList.remove('text-red-600', 'hover:underline');
        deleteButton.classList.add('text-gray-500', 'cursor-not-allowed');
        deleteButton.disabled = true;

        if (!resourceItem.querySelector('.resource-deleted-label')) {
          const deletedLabel = document.createElement('span');
          deletedLabel.className = 'resource-deleted-label text-gray-500 text-sm';
          deletedLabel.textContent = '(файл удалён)';
          resourceItem.appendChild(deletedLabel);
        }

        resourceItem.classList.add('hidden');
        resourceItem.style.display = 'none';
      }
    } catch (error) {
      console.error('Ошибка удаления дополнительного файла:', error);
      document.getElementById('error-message').textContent = 'Произошла ошибка при удалении дополнительного файла';
      document.getElementById('error-message').classList.remove('hidden');
    }
  });
});

document.getElementById('save-changes-btn').addEventListener('click', async function() {
  const form = document.getElementById('assignment-form');
  const formData = new FormData(form);
  const assignmentId = document.getElementById('assignment-form').dataset.assignmentId;

  function getValueOrExclude(value) {
    return value.trim() === '' ? undefined : value;
  }

  const updatedAssignment = {};

  const name = getValueOrExclude(formData.get('name'));
  if (name !== undefined) updatedAssignment.name = name;

  const start_date = getValueOrExclude(formData.get('start_date'));
  if (start_date !== undefined) updatedAssignment.start_date = start_date;

  const start_time = getValueOrExclude(formData.get('start_time'));
  if (start_time !== undefined) updatedAssignment.start_time = start_time;

  const due_date = getValueOrExclude(formData.get('due_date'));
  if (due_date !== undefined) updatedAssignment.due_date = due_date;

  const due_time = getValueOrExclude(formData.get('due_time'));
  if (due_time !== undefined) updatedAssignment.due_time = due_time;

  const number_of_attempts = getValueOrExclude(formData.get('number_of_attempts'));
  if (number_of_attempts !== undefined) updatedAssignment.number_of_attempts = number_of_attempts;

  const execution_timeout_seconds = getValueOrExclude(formData.get('execution_timeout_seconds'));
  if (execution_timeout_seconds !== undefined) updatedAssignment.execution_timeout_seconds = execution_timeout_seconds;

  const newDiscipline = formData.get('new_discipline_name').trim();
  const selectedDiscipline = formData.get('discipline_id');

  if (newDiscipline) {
      updatedAssignment.new_discipline_name = newDiscipline; // сервер создаст новую
  } else if (selectedDiscipline) {
      updatedAssignment.discipline_id = parseInt(selectedDiscipline, 10); // существующая дисциплина
  }



  try {
    const response = await fetch(`/assignments/${assignmentId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updatedAssignment),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('Ошибка обновления задания:', errorData);
      document.getElementById('error-message').textContent = errorData.detail || 'Произошла ошибка при обновлении задания';
      document.getElementById('error-message').classList.remove('hidden');
      return;
    }

    const assignmentFileInput = document.getElementById('assignment_file');
    const assignmentFile = assignmentFileInput.files[0];

    if (assignmentFile) {
      const fileFormData = new FormData();
      fileFormData.append('assignment_file', assignmentFile);

      const fileResponse = await fetch(`/assignments/${assignmentId}/file`, {
        method: 'PATCH',
        body: fileFormData,
      });

      if (!fileResponse.ok) {
        const fileErrorData = await fileResponse.json();
        console.error('Ошибка обновления файла:', fileErrorData);
        document.getElementById('error-message').textContent = fileErrorData.detail || 'Ошибка при обновлении файла задания';
        document.getElementById('error-message').classList.remove('hidden');
        return;
      }
    }

    const resourceFiles = resourceFilesInput ? Array.from(resourceFilesInput.files) : [];
    if (resourceFiles.length > 0) {
      const resourceFormData = new FormData();
      resourceFiles.forEach((resourceFile) => {
        resourceFormData.append('resource_files', resourceFile);
      });

      const resourcesResponse = await fetch(`/assignments/${assignmentId}/resources`, {
        method: 'POST',
        body: resourceFormData,
      });

      if (!resourcesResponse.ok) {
        const resourcesErrorData = await resourcesResponse.json();
        console.error('Ошибка добавления дополнительных файлов:', resourcesErrorData);
        document.getElementById('error-message').textContent = resourcesErrorData.detail || 'Ошибка при добавлении дополнительных файлов';
        document.getElementById('error-message').classList.remove('hidden');
        return;
      }
    }
    window.location.href = '/pages/tutor-home';

  } catch (error) {
    console.error('Ошибка при отправке данных:', error);
    document.getElementById('error-message').textContent = 'Произошла ошибка при отправке данных';
    document.getElementById('error-message').classList.remove('hidden');
  }
});
