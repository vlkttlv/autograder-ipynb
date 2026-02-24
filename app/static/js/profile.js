const API_URL = "/auth/me";
const DISC_API = "/disciplines/";
const token = localStorage.getItem("access_token");

// Обновление профиля
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
        
        setTimeout(() => {
            window.location.reload();
        }, 500);
    } else {
        msg.textContent = result.detail || "Ошибка";
        msg.classList.remove("text-green-700");
        msg.classList.add("text-red-600");
    }
});

// Функция для обновления списка дисциплин после добавления/удаления
async function refreshDisciplinesList() {
    try {
        const res = await fetch(DISC_API, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (!res.ok) {
            console.error('Ошибка загрузки дисциплин:', res.status);
            return;
        }

        const data = await res.json();
        const list = document.getElementById("disciplinesList");
        
        if (!list) {
            console.error('Элемент disciplinesList не найден');
            return;
        }
        
        list.innerHTML = "";

        if (data.length === 0) {
            list.innerHTML = '<p class="text-gray-500">Нет дисциплин</p>';
            return;
        }

        data.forEach(d => {
            const div = document.createElement("div");
            div.className = "border p-2 rounded flex justify-between items-center";
            div.innerHTML = `
                <span>${d.name}</span>
                <div class="space-x-2">
                    <button class="editDisc text-blue-600" data-id="${d.id}">Редактировать</button>
                    <button class="delDisc text-red-600" data-id="${d.id}">Удалить</button>
                </div>
            `;
            list.appendChild(div);
        });
    } catch (error) {
        console.error('Ошибка при обновлении списка дисциплин:', error);
    }
}

// Добавление дисциплины
// Добавление дисциплины
document.getElementById("addDisciplineBtn")?.addEventListener("click", async () => {
    const nameInput = document.getElementById("newDisciplineName");
    const name = nameInput.value.trim();
    
    if (!name) {
        alert('Введите название дисциплины');
        return;
    }

    try {
        const res = await fetch(`${DISC_API}?name=${encodeURIComponent(name)}`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (res.ok) {
            nameInput.value = "";
            await refreshDisciplinesList(); // Обновляем список после добавления
            setTimeout(() => {
                window.location.reload();
            }, 100);
        } else {
            const error = await res.json();
            alert('Ошибка при добавлении: ' + (error.detail || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Ошибка при добавлении дисциплины:', error);
        alert('Произошла ошибка при отправке запроса');
    }
});

// Удаление дисциплины
document.addEventListener("click", async (e) => {
    if (e.target.classList.contains("delDisc")) {
        const id = e.target.dataset.id;
        if (!id) return;

        if (!confirm("Удалить дисциплину?")) return;

        try {
            const res = await fetch(`${DISC_API}${id}`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (res.ok) {
                await refreshDisciplinesList(); // Обновляем список после удаления
                alert('Дисциплина успешно удалена');
                // Перезагрузка страницы после удаления
                setTimeout(() => {
                    window.location.reload();
                }, 100);
            } else {
                const error = await res.json();
                alert('Ошибка при удалении: ' + (error.detail || 'Неизвестная ошибка'));
            }
        } catch (error) {
            console.error('Ошибка при удалении дисциплины:', error);
        }
    }
});

// Редактирование дисциплины
document.addEventListener("click", async (e) => {
    if (e.target.classList.contains("editDisc")) {
        const id = e.target.dataset.id;
        const disciplineDiv = e.target.closest('.border');
        const nameSpan = disciplineDiv.querySelector('span:first-child');
        const currentName = nameSpan.textContent;
        
        const newName = prompt("Введите новое название дисциплины:", currentName);
        
        if (!newName || newName.trim() === '') return;
        
        try {
            // Отправляем как query parameter
            const res = await fetch(`${DISC_API}${id}?name=${encodeURIComponent(newName.trim())}`, {
                method: "PATCH",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (res.ok) {
                await refreshDisciplinesList();
                alert('Дисциплина успешно обновлена');
                // Перезагрузка страницы после редактирования
                setTimeout(() => {
                    window.location.reload();
                }, 100);
            } else {
                const error = await res.json();
                console.error('Ошибка сервера:', error);
                alert('Ошибка при редактировании: ' + (error.detail || 'Неизвестная ошибка'));
            }
        } catch (error) {
            console.error('Ошибка при редактировании дисциплины:', error);
            alert('Произошла ошибка при отправке запроса');
        }
    }
});

// Проверка наличия токена при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    if (!token) {
        console.error('Токен не найден');
        // Можно перенаправить на страницу входа
        // window.location.href = '/login';
    }
});