async function refreshToken() {
  try {
    const response = await fetch('/auth/token/refresh', {
      method: 'POST',
      credentials: 'include',
    });

    if (response.status === 401) {
      window.location.href = '/pages/auth/login';
      return;
    }

    if (!response.ok) {
      throw new Error('Не удалось обновить токен');
    }

    await response.json();
  } catch (error) {
    console.error('Ошибка при обновлении токена:', error);
    window.location.href = '/pages/auth/login';
  }
}

refreshToken();
setInterval(refreshToken, 30 * 60 * 1000);
