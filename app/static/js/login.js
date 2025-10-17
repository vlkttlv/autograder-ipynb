const form = document.getElementById('login-form');

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const formData = {
    email: form.email.value,
    password: form.password.value,
  };

  try {
    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData),
      credentials: 'include'
    });

    const data = await response.json();

    if (response.ok) {
      localStorage.setItem('refresh_token', data.refresh_token);

      const decodedToken = jwt_decode(data.access_token);
      const userRole = decodedToken.role;

      if (userRole === 'STUDENT') {
        window.location.href = '/pages/student-home';
      } else if (userRole === 'TUTOR') {
        window.location.href = '/pages/tutor-home';
      }
    } else {
      alert(data.detail || 'Ошибка при авторизации');
    }
  } catch (error) {
    console.error('Ошибка:', error);
    alert('Ошибка при подключении к серверу');
  }
});
