async function handleLogout(e) {
  e.preventDefault();

  try {
    // Best-effort logout from JupyterHub to avoid stale Hub session
    // when another user signs in from the same browser.
    await fetch("/jhub/hub/logout", {
      method: "GET",
      credentials: "include",
    });

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
