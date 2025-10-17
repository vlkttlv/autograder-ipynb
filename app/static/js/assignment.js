document.addEventListener('DOMContentLoaded', function () {
  const deleteBtn = document.getElementById('delete-btn');
  if (!deleteBtn) return;

  deleteBtn.addEventListener('click', async function() {
    const assignmentId = deleteBtn.dataset.assignmentId;
    const assignmentName = deleteBtn.dataset.assignmentName;

    const confirmed = confirm(`Вы уверены, что хотите удалить задание "${assignmentName}"?\nЭту операцию нельзя отменить. Вся информация, связанная с заданием, включая все оценки, будет удалена.`);

    if (!confirmed) return;

    try {
      const response = await fetch(`/assignments/${assignmentId}`, { method: 'DELETE' });
      if (response.ok) {
        window.location.href = '/pages/tutor-home';
      } else {
        const errorData = await response.json();
        alert('Ошибка: ' + (errorData.detail || 'Не удалось удалить задание'));
      }
    } catch (error) {
      console.error('Ошибка при удалении задания:', error);
      alert('Произошла ошибка при удалении задания');
    }
  });
});
