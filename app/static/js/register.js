document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('register-form');
  const roleSelect = document.getElementById('role');
  const groupContainer = document.getElementById('student-group-container');

  roleSelect.addEventListener('change', () => {
    if (roleSelect.value === 'STUDENT') {
      groupContainer.style.display = 'block';
    } else {
      groupContainer.style.display = 'none';
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
      first_name: form.first_name.value,
      last_name: form.last_name.value,
      email: form.email.value,
      password: form.password.value,
      role: form.role.value,
      group: form.role.value === 'STUDENT' ? form.group.value : null
    };

    try {
      const response = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (response.ok) {
        alert('Регистрация успешна! Войдите в систему.');
        window.location.href = '/login';
      } else {
        alert(data.detail || 'Ошибка при регистрации');
      }
    } catch (error) {
      console.error('Ошибка:', error);
      alert('Ошибка при подключении к серверу');
    }
  });
});
