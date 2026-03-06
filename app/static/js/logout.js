async function handleLogout(e) {
  e.preventDefault();

  try {
    const response = await fetch("/auth/logout", {
      method: "POST",
      credentials: "include",
    });

    if (response.ok) {
      window.location.href = "/pages/auth/login";
      return;
    }

    alert("Ошибка при выходе");
  } catch (err) {
    console.error("Ошибка:", err);
    alert("Не удалось выйти. Попробуйте еще раз.");
  }
}

const logoutForms = document.querySelectorAll("#logout-form");
logoutForms.forEach((form) => {
  form.addEventListener("submit", handleLogout);
});
