document.addEventListener("DOMContentLoaded", function () {
  const submitButton = document.getElementById("submit-btn");
  const uploadMessageBlock = document.getElementById("upload-message");

  const editorSection = document.getElementById("embedded-editor-section");
  const editorStatus = document.getElementById("editor-status");
  const editorFrameContainer = document.getElementById("editor-frame-container");
  const notebookIframe = document.getElementById("notebook-iframe");
  const saveNotebookButton = document.getElementById("save-notebook-btn");
  const evaluateNotebookButton = document.getElementById("evaluate-notebook-btn");
  const editorMessageBlock = document.getElementById("editor-message");

  let jupyterToken = null;

  async function resetJupyterHubSession() {
    try {
      await fetch("/jhub/hub/logout", {
        method: "GET",
        credentials: "include",
      });
    } catch (error) {
      console.warn("Не удалось сбросить сессию JupyterHub:", error);
    }
  }

  function showMessage(element, text, type = "success") {
    if (!element) return;
    element.textContent = text;
    if (type === "success") {
      element.className = "mt-2 text-green-600 text-sm";
    } else if (type === "warning") {
      element.className = "mt-2 text-yellow-700 text-sm";
    } else {
      element.className = "mt-2 text-red-600 text-sm";
    }
  }

  async function uploadAndEvaluateFile() {
    const assignmentId = submitButton.dataset.assignmentId;
    const fileInput = document.getElementById("submission-file");
    const file = fileInput.files[0];

    if (!file) {
      showMessage(uploadMessageBlock, "Пожалуйста, выберите файл для отправки.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("submission_file", file);

    try {
      showMessage(uploadMessageBlock, "Отправка файла...", "success");
      const uploadResponse = await fetch(`/assignments/${assignmentId}/submissions`, {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json();
        showMessage(
          uploadMessageBlock,
          "Ошибка при загрузке файла: " + (errorData.detail || "Не удалось загрузить файл"),
          "error"
        );
        return;
      }

      showMessage(uploadMessageBlock, "Файл загружен. Проверяем решение...", "success");
      const evaluateResponse = await fetch(`/assignments/${assignmentId}/submissions/evaluate`, {
        method: "POST",
      });

      if (!evaluateResponse.ok) {
        const errorData = await evaluateResponse.json();
        showMessage(
          uploadMessageBlock,
          "Ошибка при проверке: " + (errorData.detail || "Не удалось проверить решение"),
          "error"
        );
        return;
      }

      const data = await evaluateResponse.json();
      showMessage(uploadMessageBlock, `Решение проверено. Ваши баллы: ${data.score}`, "success");
    } catch (error) {
      console.error("Ошибка при отправке задания:", error);
      showMessage(uploadMessageBlock, "Произошла ошибка при отправке задания.", "error");
    }
  }

  async function initEmbeddedEditor() {
    if (!editorSection) return;
    const assignmentId = editorSection.dataset.assignmentId;
    try {
      const response = await fetch(`/assignments/${assignmentId}/notebook/session`, {
        method: "POST",
      });
      if (!response.ok) {
        showMessage(editorStatus, "Редактор недоступен. Используйте загрузку файла ниже.", "warning");
        if (saveNotebookButton) saveNotebookButton.disabled = true;
        if (evaluateNotebookButton) evaluateNotebookButton.disabled = true;
        return;
      }

      const data = await response.json();
      if (!data.enabled || !data.iframe_url) {
        showMessage(editorStatus, "Редактор недоступен. Используйте загрузку файла ниже.", "warning");
        if (saveNotebookButton) saveNotebookButton.disabled = true;
        if (evaluateNotebookButton) evaluateNotebookButton.disabled = true;
        return;
      }

      await resetJupyterHubSession();
      notebookIframe.src = data.iframe_url;
      editorFrameContainer.style.display = "block";
      editorStatus.textContent = "Редактор готов.";
      editorStatus.className = "mt-2 text-sm text-green-700";

      const iframeUrl = new URL(data.iframe_url, window.location.origin);
      jupyterToken = iframeUrl.searchParams.get("token");
    } catch (error) {
      console.error("Не удалось инициализировать редактор:", error);
      showMessage(editorStatus, "Редактор недоступен. Используйте загрузку файла ниже.", "warning");
      if (saveNotebookButton) saveNotebookButton.disabled = true;
      if (evaluateNotebookButton) evaluateNotebookButton.disabled = true;
    }
  }

  async function saveEmbeddedNotebook() {
    if (!editorSection) return;
    const assignmentId = editorSection.dataset.assignmentId;
    if (!jupyterToken) {
      showMessage(editorMessageBlock, "Токен редактора не найден. Обновите страницу.", "error");
      return;
    }

    try {
      showMessage(editorMessageBlock, "Сохраняем черновик...", "success");
      const response = await fetch(`/assignments/${assignmentId}/notebook/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jupyter_token: jupyterToken }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        showMessage(
          editorMessageBlock,
          "Ошибка сохранения: " + (errorData.detail || "Не удалось сохранить"),
          "error"
        );
        return;
      }
      showMessage(editorMessageBlock, "Черновик сохранен.", "success");
    } catch (error) {
      console.error("Ошибка сохранения черновика:", error);
      showMessage(editorMessageBlock, "Ошибка сохранения черновика.", "error");
    }
  }

  async function evaluateEmbeddedNotebook() {
    if (!editorSection) return;
    const assignmentId = editorSection.dataset.assignmentId;
    if (!jupyterToken) {
      showMessage(editorMessageBlock, "Токен редактора не найден. Обновите страницу.", "error");
      return;
    }

    try {
      showMessage(editorMessageBlock, "Сохраняем и отправляем на проверку...", "success");
      const response = await fetch(`/assignments/${assignmentId}/notebook/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jupyter_token: jupyterToken }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        showMessage(
          editorMessageBlock,
          "Ошибка проверки: " + (errorData.detail || "Не удалось проверить решение"),
          "error"
        );
        return;
      }

      const data = await response.json();
      showMessage(
        editorMessageBlock,
        `Решение проверено. Ваши баллы: ${data.score}`,
        "success"
      );
    } catch (error) {
      console.error("Ошибка проверки решения:", error);
      showMessage(editorMessageBlock, "Ошибка при проверке решения.", "error");
    }
  }

  if (submitButton) {
    submitButton.addEventListener("click", uploadAndEvaluateFile);
  }
  if (saveNotebookButton) {
    saveNotebookButton.addEventListener("click", saveEmbeddedNotebook);
  }
  if (evaluateNotebookButton) {
    evaluateNotebookButton.addEventListener("click", evaluateEmbeddedNotebook);
  }

  initEmbeddedEditor();
});
