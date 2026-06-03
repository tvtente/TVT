(function () {
  function moveIntoLanguageRow(rowClassName, fieldName) {
    var sourceRows = document.querySelectorAll("." + rowClassName);
    if (!sourceRows.length) {
      return;
    }
    var targetInput = document.getElementById("id_" + fieldName);
    if (!targetInput) {
      return;
    }
    var targetRow = targetInput.closest(".form-row, .form-group");
    if (!targetRow || !targetRow.parentNode) {
      return;
    }
    var anchor = targetRow.nextSibling;
    sourceRows.forEach(function (row) {
      targetRow.parentNode.insertBefore(row, anchor);
    });
  }

  function hideFieldRows(fieldNames) {
    fieldNames.forEach(function (name) {
      var rows = document.querySelectorAll(
        ".field-" + name + ", .form-row.field-" + name + ", .form-group.field-" + name
      );
      rows.forEach(function (row) {
        row.style.display = "none";
      });
    });
  }

  function alignPageMediaRowsWithLanguageTabs() {
    moveIntoLanguageRow("field-featured_image_media_picker_es", "title_es");

    moveIntoLanguageRow("field-featured_image_media_picker_en", "title_en");

    moveIntoLanguageRow("field-featured_image_media_picker_ca", "title_ca");

    hideFieldRows([
      "featured_image_asset",
      "featured_image_asset_es",
      "featured_image_asset_en",
      "featured_image_asset_ca",
    ]);
  }

  function alignWithRetries() {
    var attempts = 0;
    var maxAttempts = 8;
    var timer = setInterval(function () {
      alignPageMediaRowsWithLanguageTabs();
      attempts += 1;
      if (attempts >= maxAttempts) {
        clearInterval(timer);
      }
    }, 120);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", alignWithRetries);
  } else {
    alignWithRetries();
  }
})();
