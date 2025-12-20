const API_URL = "/auth/me";   // путь к PATCH /me
const token = localStorage.getItem("access_token");

document.getElementById("update-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {};

    const firstName = document.getElementById("first_name")?.value.trim();
    const lastName = document.getElementById("last_name")?.value.trim();
    const groupInput = document.getElementById("group");

    if (firstName) payload.first_name = firstName;
    if (lastName) payload.last_name = lastName;

    if (groupInput) {
        const group = groupInput.value.trim();
        if (group) payload.group = group;
    }

    const response = await fetch(API_URL, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
    });

    const result = await response.json();

    const msg = document.getElementById("message");

    if (response.ok) {
        msg.textContent = "Данные обновлены. Перезагрузите страницу.";
        msg.classList.remove("text-red-600");
        msg.classList.add("text-green-700");
    } else {
        msg.textContent = result.detail || "Ошибка";
        msg.classList.remove("text-green-700");
        msg.classList.add("text-red-600");
    }
});
