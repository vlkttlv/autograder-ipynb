async function refreshToken() {
  try {
    // Отправка запроса на обновление токена
    const response = await fetch('http://127.0.0.1:8000/auth/token/refresh', {
      method: 'POST',
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Не удалось обновить токен');
    }

    const data = await response.json();
    console.log('Токен успешно обновлён:', data);

  } catch (error) {
    console.error('Ошибка при обновлении токена:', error);
    autoLogout();
  }
}

// Запуск обновления токена сразу при загрузке страницы
refreshToken();

// Обновление токена каждые 30 минут
setInterval(refreshToken, 30 * 60 * 1000);
