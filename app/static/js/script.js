console.log("script.js загружен");

async function refreshToken() {
  try {
    // Отправка запроса на обновление токена
    const response = await fetch('http://127.0.0.1:8000/auth/token/refresh', {
      method: 'POST',
      credentials: 'include',  // включаем cookies для авторизации
    });

    // Если ответ не успешный
    if (!response.ok) {
      throw new Error('Не удалось обновить токен');
    }

    // Обработка успешного ответа
    const data = await response.json();
    console.log('Токен успешно обновлён:', data);

  } catch (error) {
    console.error('Ошибка при обновлении токена:', error);
    autoLogout();
  }
}

// Функция для авто-выхода
function autoLogout() {
  const overlay = document.getElementById('logout-overlay');
  overlay.classList.remove('hidden');
  setTimeout(() => {
    window.location.href = '/login';
  }, 2000);
}

// Запуск обновления токена сразу при загрузке страницы
refreshToken();

// Обновление токена каждые 30 минут
setInterval(refreshToken, 30 * 60 * 1000);
