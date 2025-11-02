document.addEventListener("DOMContentLoaded", () => {
  const studentBtn = document.getElementById("student-btn");
  const tutorBtn = document.getElementById("tutor-btn");
  const roleInput = document.getElementById("role");
  const groupContainer = document.getElementById("student-group-container");
  const registerForm = document.getElementById("register-form");

  // 🔹 Переключение ролей
  studentBtn.addEventListener("click", () => {
    studentBtn.classList.add("active");
    tutorBtn.classList.remove("active");
    roleInput.value = "STUDENT";
    groupContainer.style.display = "block";
  });

  tutorBtn.addEventListener("click", () => {
    tutorBtn.classList.add("active");
    studentBtn.classList.remove("active");
    roleInput.value = "TUTOR";
    groupContainer.style.display = "none";
  });

  // 🔹 Отправка формы
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    // Убираем старое сообщение об ошибке
    let errorDiv = document.getElementById("form-error");
    if (!errorDiv) {
      errorDiv = document.createElement("div");
      errorDiv.id = "form-error";
      errorDiv.classList.add("text-red-600", "mb-4", "text-center", "font-medium");
      registerForm.prepend(errorDiv); // вставляем сверху формы
    }
    errorDiv.textContent = ""; // очищаем

    const formData = new FormData(registerForm);
    const data = Object.fromEntries(formData.entries());
    if (data.role !== "STUDENT") data.group = null;

    try {
      const response = await fetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        // Выводим единое сообщение для всех ошибок
        if (errorData.detail && Array.isArray(errorData.detail)) {
          errorDiv.textContent = "Проверьте корректность введенных данных";
        } else {
          errorDiv.textContent = errorData.detail || "Произошла ошибка при регистрации";
        }
        return;
      }

      alert("Регистрация успешна!");
      window.location.href = "/pages/auth/login";

    } catch (err) {
      console.error("Ошибка:", err);
      errorDiv.textContent = "Произошла ошибка при регистрации";
    }
  });

});
