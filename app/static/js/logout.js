const logoutForm = document.getElementById("logout-form");

logoutForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const response = await fetch("/auth/logout", {
      method: "POST",
      credentials: "include",
    });

    if (response.ok) {
      // Перенаправляем на страницу авторизации
      window.location.href = "/pages/auth/login";
    } else {
      alert("Ошибка при выходе");
    }
  } catch (err) {
    console.error("Ошибка:", err);
    alert("Не удалось выйти. Попробуйте еще раз.");
  }
});
