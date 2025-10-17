document.addEventListener('DOMContentLoaded', function () {
  const submitButton = document.getElementById('submit-btn');
  const messageBlock = document.getElementById('message');

  if (!submitButton) return;

  function showMessage(text, type = 'success') {
    messageBlock.textContent = text;
    if (type === 'success') {
      messageBlock.className = "mt-2 text-green-600 text-sm";
    } else {
      messageBlock.className = "mt-2 text-red-600 text-sm";
    }
  }

  submitButton.addEventListener('click', async function() {
    const assignmentId = submitButton.dataset.assignmentId;
    const fileInput = document.getElementById('submission-file');
    const file = fileInput.files[0];

    if (!file) {
      showMessage("Пожалуйста, выберите файл для отправки.", 'error');
      return;
    }

    const formData = new FormData();
    formData.append('submission_file', file);

    try {
      showMessage("Отправка файла...", 'success');

      const response = await fetch(`/assignments/${assignmentId}/submissions`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        showMessage("Файл загружен! Проверяем решение...", 'success');

        const checkResponse = await fetch(`/assignments/${assignmentId}/submissions/evaluate`, {
          method: 'POST',
        });

        if (checkResponse.ok) {
          const data = await checkResponse.json();
          showMessage(`Решение проверено! Ваши баллы: ${data.score}`, 'success');
        } else {
          const errorData = await checkResponse.json();
          showMessage('Ошибка при проверке: ' + (errorData.detail || 'Не удалось проверить решение'), 'error');
        }
      } else {
        const errorData = await response.json();
        showMessage('Ошибка при загрузке файла: ' + (errorData.detail || 'Не удалось загрузить файл'), 'error');
      }
    } catch (error) {
      console.error('Ошибка при отправке задания:', error);
      showMessage('Произошла ошибка при отправке задания.', 'error');
    }
  });
});
