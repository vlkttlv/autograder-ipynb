document.getElementById('save-changes-btn').addEventListener('click', async function() {
  const form = document.getElementById('assignment-form');
  const formData = new FormData(form);
  const assignmentId = "{{ assignment.id }}";

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

    window.location.href = '/pages/tutor-home';

  } catch (error) {
    console.error('Ошибка при отправке данных:', error);
    document.getElementById('error-message').textContent = 'Произошла ошибка при отправке данных';
    document.getElementById('error-message').classList.remove('hidden');
  }
});
