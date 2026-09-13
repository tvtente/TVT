/* Confirm the cascading visibility change before the Category admin saves. */
(function () {
  "use strict";

  function descendants() {
    const node = document.getElementById("category-visible-descendants");
    if (!node) return [];
    try {
      const value = JSON.parse(node.textContent || "[]");
      return Array.isArray(value) ? value : [];
    } catch (error) {
      return [];
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const checkbox = document.getElementById("id_is_visible");
    const form = document.getElementById("category_form");
    const childNames = descendants();
    if (!checkbox || !form || !checkbox.checked || !childNames.length) return;

    form.addEventListener("submit", function (event) {
      if (checkbox.checked) return;
      const message = [
        "Esta categoría tiene subcategorías visibles.",
        "También se desactivarán:",
        childNames.map(function (name) { return "• " + name; }).join("\n"),
        "\n¿Deseas continuar?",
      ].join("\n");
      if (!window.confirm(message)) event.preventDefault();
    });
  });
})();
