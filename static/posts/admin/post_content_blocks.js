/* Dynamic fields for the PostContentBlock inline in the Django admin. */
(function () {
  "use strict";

  const CONTENT = "content";
  const RELATED_POST = "related_post";
  const CONTENT_FIELDS = ["summary", "content", "image_asset", "image_alt", "show_in_listings"];
  const RELATED_FIELDS = ["related_post"];

  function fieldCell(row, fieldName) {
    return row.querySelector(".field-" + fieldName);
  }

  function setVisible(row, fieldName, visible) {
    const cell = fieldCell(row, fieldName);
    if (!cell) return;
    cell.hidden = !visible;
  }

  function updateRow(row) {
    if (!row) return;
    const typeSelect = row.querySelector('select[name$="-block_type"]');
    if (!typeSelect) return;

    const type = typeSelect.value;
    const isContent = type === CONTENT;
    const isReference = type === RELATED_POST;
    CONTENT_FIELDS.forEach(function (fieldName) {
      setVisible(row, fieldName, isContent);
    });
    RELATED_FIELDS.forEach(function (fieldName) {
      setVisible(row, fieldName, isReference);
    });
  }

  function updateAllRows() {
    document.querySelectorAll("#content_blocks-group .inline-related").forEach(updateRow);
  }

  function slugify(value) {
    return value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function syncAnchorFromHeading(row) {
    if (!row) return;
    const heading = row.querySelector('input[name$="-heading"]');
    const anchor = row.querySelector('input[name$="-anchor"]');
    if (!heading || !anchor) return;

    const automaticValue = slugify(heading.value);
    const generatedValue = anchor.dataset.generatedAnchor || "";
    const canReplace = !anchor.value || anchor.value === generatedValue;
    if (canReplace && automaticValue) {
      anchor.value = automaticValue;
      anchor.dataset.generatedAnchor = automaticValue;
    }
  }

  function initialiseAnchor(row) {
    if (!row) return;
    const heading = row.querySelector('input[name$="-heading"]');
    const anchor = row.querySelector('input[name$="-anchor"]');
    if (!heading || !anchor) return;
    const expected = slugify(heading.value);
    if (!anchor.value || anchor.value === expected) {
      anchor.dataset.generatedAnchor = anchor.value || expected;
      syncAnchorFromHeading(row);
    }
  }

  function renameAddButton() {
    const addLink = document.querySelector("#content_blocks-group .add-row a");
    if (addLink && addLink.textContent !== "Añadir bloque de contenido") {
      addLink.textContent = "Añadir bloque de contenido";
    }
  }

  function placeBelowMobileImagePicker() {
    const inlineGroup = document.getElementById("content_blocks-group");
    const mobileImageRow = document.querySelector(".form-row.field-mobile_image_picker");
    if (!inlineGroup || !mobileImageRow || inlineGroup.previousElementSibling === mobileImageRow) {
      return;
    }
    mobileImageRow.insertAdjacentElement("afterend", inlineGroup);
  }

  function initialiseMediaPicker(row) {
    const pickerRoot = row && row.querySelector("[data-gallery-picker-root]");
    if (pickerRoot && window.initializeGalleryMediaPickerRoot) {
      window.initializeGalleryMediaPickerRoot(pickerRoot);
    }
  }

  function fitSummernoteFrame(frame) {
    if (!frame || frame.dataset.postEditorFitted === "true") return;
    frame.dataset.postEditorFitted = "true";
    function applyResponsiveStyle() {
      try {
        const doc = frame.contentDocument;
        if (!doc || doc.getElementById("post-editor-responsive-style")) return;
        const style = doc.createElement("style");
        style.id = "post-editor-responsive-style";
        style.textContent =
          "html, body { min-width: 0 !important; max-width: 100% !important; overflow-x: hidden !important; }" +
          "body { box-sizing: border-box !important; }" +
          ".note-editable { box-sizing: border-box !important; max-width: 100% !important; overflow-x: hidden !important; overflow-wrap: anywhere; }" +
          ".note-editable img, .note-editable table { max-width: 100% !important; }";
        (doc.head || doc.documentElement).appendChild(style);
      } catch (error) {
        // The Summernote iframe is same-origin in this project.  If that ever
        // changes, the editor remains usable with its normal browser styles.
      }
    }
    frame.addEventListener("load", applyResponsiveStyle);
    applyResponsiveStyle();
  }

  function fitAllSummernoteFrames() {
    document.querySelectorAll("#post_form .summernote-div iframe").forEach(fitSummernoteFrame);
  }

  document.addEventListener("change", function (event) {
    if (!event.target.matches('#content_blocks-group select[name$="-block_type"]')) return;
    updateRow(event.target.closest(".inline-related"));
  });

  document.addEventListener("input", function (event) {
    const row = event.target.closest("#content_blocks-group .inline-related");
    if (!row) return;
    if (event.target.matches('input[name$="-heading"]')) {
      syncAnchorFromHeading(row);
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    placeBelowMobileImagePicker();
    updateAllRows();
    document.querySelectorAll("#content_blocks-group .inline-related").forEach(initialiseAnchor);
    document.querySelectorAll("#content_blocks-group .inline-related").forEach(initialiseMediaPicker);
    fitAllSummernoteFrames();
    renameAddButton();
    // Django emits this when the user clicks "Add another" in an inline.
    // Using its event avoids observing and mutating the same DOM tree.
    if (window.django && window.django.jQuery) {
      window.django.jQuery(document).on("formset:added", function (event, row, formsetName) {
        if (formsetName !== "content_blocks") return;
        const rowElement = row && row.jquery ? row.get(0) : row;
        updateRow(rowElement);
        initialiseAnchor(rowElement);
        initialiseMediaPicker(rowElement);
        fitAllSummernoteFrames();
        renameAddButton();
      });
    }
  });

  // Django 5 dispatches a native CustomEvent for newly-added inline rows.
  document.addEventListener("formset:added", function (event) {
    const detail = event.detail || {};
    if (detail.formsetName !== "content_blocks") return;
    updateRow(detail.row);
    initialiseAnchor(detail.row);
    initialiseMediaPicker(detail.row);
    fitAllSummernoteFrames();
    renameAddButton();
  });
})();
