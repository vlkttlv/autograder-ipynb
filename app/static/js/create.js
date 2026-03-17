const resourceFilesInput = document.getElementById('resource_files');
const resourceFilesSelected = document.getElementById('resource-files-selected');

if (resourceFilesInput && resourceFilesSelected) {
  resourceFilesInput.addEventListener('change', function() {
    const files = Array.from(this.files || []);

    if (!files.length) {
      resourceFilesSelected.textContent = 'Файлы не выбраны';
      return;
    }

    resourceFilesSelected.textContent = files.map((file) => file.name).join(', ');
  });
}

document.getElementById('submit-btn').addEventListener('click', async function() {
  const form = document.getElementById('assignment-form');
  const formData = new FormData(form);

  // Убираем пустое discipline_id, чтобы FastAPI не ругался
  if (!formData.get('discipline_id')) {
    formData.delete('discipline_id');
  }

  const submitButton = document.getElementById('submit-btn');

  // Показать сообщение "Создаем тест..." + спиннер
  let creatingMessage = document.getElementById('creating-message');
  if (!creatingMessage) {
    creatingMessage = document.createElement('div');
    creatingMessage.id = 'creating-message';
    creatingMessage.className = 'mt-4 flex items-center text-blue-600 font-semibold';

    const spinner = document.createElement('div');
    spinner.className = 'w-5 h-5 mr-2 border-4 border-blue-500 border-t-transparent border-solid rounded-full animate-spin';

    const text = document.createElement('span');
    text.textContent = 'Создаем тест...';

    creatingMessage.appendChild(spinner);
    creatingMessage.appendChild(text);

    submitButton.parentNode.insertBefore(creatingMessage, submitButton.nextSibling);
  }

  // Отключаем кнопку
  submitButton.disabled = true;
  submitButton.classList.add('opacity-50', 'cursor-not-allowed');

  try {
    const response = await fetch('/assignments/', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('Error response:', errorData);
      document.getElementById('error-message').textContent = errorData.detail || 'Произошла ошибка';
      document.getElementById('error-message').classList.remove('hidden');

      creatingMessage.remove();
      submitButton.disabled = false;
      submitButton.classList.remove('opacity-50', 'cursor-not-allowed');

    } else {
      const result = await response.json();
      const assignmentId = result.assignment_id;
      window.location.href = `/pages/assignments/${assignmentId}`;
    }
  } catch (error) {
    console.error('Ошибка при отправке формы:', error);
    document.getElementById('error-message').textContent = 'Произошла ошибка при отправке данных';
    document.getElementById('error-message').classList.remove('hidden');

    creatingMessage.remove();
    submitButton.disabled = false;
    submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
  }
});
