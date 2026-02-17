/**
 * Herald — Alpine.js API Store & Toast notifications
 */
document.addEventListener("alpine:init", () => {
  Alpine.store("api", {
    loading: false,

    /**
     * Call an RPC action: POST /api/{action}
     * @param {string} action - e.g. "create_channel"
     * @param {object} payload - request body
     * @returns {Promise<object>} parsed JSON response
     */
    async call(action, payload = {}) {
      this.loading = true;
      try {
        const res = await fetch(`/api/${action}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();

        if (!data.ok) {
          showToast("error", data.msg || "操作失败");
          throw new Error(data.msg);
        }

        showToast("success", data.msg || "操作成功");
        return data;
      } catch (err) {
        if (err.message && !err.message.includes("操作失败")) {
          showToast("error", err.message);
        }
        throw err;
      } finally {
        this.loading = false;
      }
    },
  });
});

/**
 * Show a toast notification.
 * @param {"success"|"error"|"info"} type
 * @param {string} msg
 * @param {number} duration - ms
 */
function showToast(type, msg, duration = 3000) {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const alertClass = {
    success: "alert-success",
    error: "alert-error",
    info: "alert-info",
  }[type] || "alert-info";

  const iconClass = {
    success: "ri-check-line",
    error: "ri-error-warning-line",
    info: "ri-information-line",
  }[type] || "ri-information-line";

  const el = document.createElement("div");
  el.className = `alert ${alertClass} shadow-lg toast-enter text-sm py-3`;
  el.innerHTML = `<i class="${iconClass} text-lg"></i><span>${msg}</span>`;
  container.appendChild(el);

  setTimeout(() => {
    el.classList.remove("toast-enter");
    el.classList.add("toast-exit");
    el.addEventListener("animationend", () => el.remove());
  }, duration);
}
