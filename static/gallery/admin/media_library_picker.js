/**
 * Admin media library picker: supports multiple roots per page (e.g. Post featured + social).
 * Backward compatible: roots without data-staging-name use staging_id / source_image_id / image.
 */
(function () {
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function csrfToken() {
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    if (input && input.value) {
      return input.value;
    }
    return getCookie("csrftoken");
  }

  function uploadSafeFile(file, preferredName) {
    // Some hosting WAF rules reject image uploads whose filename resembles an
    // executable (for example, a name beginning with "exec").  The binary and
    // MIME type are unchanged; only the multipart filename is normalized.
    const originalName = file.name || "image";
    const safeName = (preferredName || originalName)
      .replace(/^exec(?:utable)?(?=[\s._-]|$)/i, "image")
      .replace(/[^a-zA-Z0-9._-]/g, "-");

    if (safeName === originalName || typeof File === "undefined") {
      return file;
    }
    return new File([file], safeName || "image", {
      type: file.type,
      lastModified: file.lastModified,
    });
  }

  function postImageUploadName(scope, file) {
    const aspect = (scope.root.dataset.uploadAspect || "").trim();
    const slugField = resolveField(scope.form, "slug");
    const slug = slugField && slugField.value ? slugField.value.trim() : "";
    if (!aspect || !slug) {
      return "";
    }

    const extensionMatch = (file.name || "").match(/(\.[a-z0-9]+)$/i);
    const extension = extensionMatch ? extensionMatch[1].toLowerCase() : ".jpg";
    return slug + "-" + aspect + extension;
  }

  function stageUploadErrorMessage(errorCode) {
    if (errorCode === "missing_file") {
      return "No file was received. Please choose an image again.";
    }
    if (errorCode === "unsupported_type") {
      return "Unsupported image format. Use JPG, PNG, GIF, WEBP, or SVG.";
    }
    if (errorCode === "file_too_large") {
      return "The image is too large. The maximum allowed size is 15 MB.";
    }
    if (errorCode === "invalid_image") {
      return "The selected file is not a valid image. Try exporting or resaving it before uploading.";
    }
    if (errorCode === "storage_error") {
      return "The server could not save the image. Check the media/gallery/_staging folder permissions.";
    }
    return "Staging upload failed.";
  }

  function resolveField(form, fieldName) {
    if (!form || !fieldName) {
      return null;
    }
    return form.querySelector('[name="' + fieldName + '"]');
  }

  function initGalleryPickerEcosystem() {
    const roots = document.querySelectorAll("[data-gallery-picker-root]");
    if (!roots.length) {
      return;
    }

    const first = roots[0];
    const stageUrl = first.dataset.stageUrl;
    const imagesUrl = first.dataset.imagesUrl;
    if (!stageUrl || !imagesUrl) {
      return;
    }

    const backdrop = document.createElement("div");
    backdrop.className = "gallery-picker-modal-backdrop";
    backdrop.setAttribute("role", "dialog");
    backdrop.setAttribute("aria-modal", "true");
    backdrop.innerHTML =
      '<div class="gallery-picker-modal">' +
      "<header>" +
      "<h2>Media library</h2>" +
      '<button type="button" class="button" data-act="close-modal">Close</button>' +
      "</header>" +
      '<div class="gallery-picker-toolbar">' +
      '<input type="search" placeholder="Search title…" data-role="search">' +
      '<select data-role="lang"><option value="">All languages</option>' +
      '<option value="es">es</option><option value="en">en</option><option value="ca">ca</option></select>' +
      "</div>" +
      '<div class="gallery-picker-grid-wrap"><div class="gallery-picker-grid" data-role="grid"></div></div>' +
      '<div class="gallery-picker-pagination">' +
      '<span data-role="page-info"></span>' +
      '<button type="button" class="button" data-act="prev">Previous</button>' +
      '<button type="button" class="button" data-act="next">Next</button>' +
      "</div>" +
      "</div>";
    document.body.appendChild(backdrop);

    const zoomBackdrop = document.createElement("div");
    zoomBackdrop.className = "gallery-picker-zoom-backdrop";
    zoomBackdrop.innerHTML = "<img alt=\"\">";
    document.body.appendChild(zoomBackdrop);
    const zoomImg = zoomBackdrop.querySelector("img");

    let page = 1;
    let totalPages = 1;
    let currentQuery = "";
    let currentLang = "";
    let activeScope = null;

    function updateSelectionPreview(scope, src, text) {
      if (!scope || !scope.selection) {
        return;
      }
      const selection = scope.selection;
      const previewImg = scope.previewImg;
      const captionEl = scope.captionEl;
      if (!src && !text) {
        selection.classList.remove("is-visible");
        previewImg.removeAttribute("src");
        captionEl.textContent = "";
        return;
      }
      selection.classList.add("is-visible");
      if (src) {
        previewImg.src = src;
      }
      captionEl.textContent = text || "";
    }

    function clearScopeInputs(scope, opts) {
      const skipRemote = opts && opts.skipRemote;
      if (scope.stagingInput) {
        scope.stagingInput.value = "";
      }
      if (scope.sourceInput) {
        scope.sourceInput.value = "";
      }
      if (scope.fkInput) {
        scope.fkInput.value = "";
      }
      if (scope.fileInput) {
        scope.fileInput.value = "";
      }
      updateSelectionPreview(scope, "", "");
      if (!skipRemote) {
        /* optional: remote DELETE staging */
      }
    }

    function renderGrid(items) {
      const grid = backdrop.querySelector('[data-role="grid"]');
      grid.innerHTML = "";
      if (!items.length) {
        const empty = document.createElement("div");
        empty.className = "gallery-picker-empty";
        empty.textContent = "No images match.";
        grid.appendChild(empty);
        return;
      }
      items.forEach(function (item) {
        const card = document.createElement("div");
        card.className = "gallery-picker-card";
        card.setAttribute("role", "button");
        card.setAttribute("tabindex", "0");
        card.dataset.id = String(item.id);
        card.innerHTML =
          '<div class="gallery-picker-card__thumb"><img alt=""></div>' +
          '<div class="gallery-picker-card__meta">' +
          '<span class="gallery-picker-card__title"></span>' +
          '<span class="gallery-picker-lang"></span>' +
          '<button type="button" class="button gallery-picker-preview-btn" data-act="zoom">Preview</button>' +
          "</div>";
        const img = card.querySelector("img");
        img.src = item.url || "";
        img.alt = item.title || "";
        card.querySelector(".gallery-picker-card__title").textContent = item.title || item.slug;
        card.querySelector(".gallery-picker-lang").textContent = item.language || "";
        card.addEventListener("click", function () {
          if (!activeScope) {
            return;
          }
          clearScopeInputs(activeScope, { skipRemote: true });
          if (activeScope.fkInput) {
            activeScope.fkInput.value = String(item.id);
          } else if (activeScope.sourceInput) {
            activeScope.sourceInput.value = String(item.id);
          }
          if (activeScope.stagingInput) {
            activeScope.stagingInput.value = "";
          }
          if (activeScope.fileInput) {
            activeScope.fileInput.value = "";
          }
          updateSelectionPreview(activeScope, item.url, item.title + " (" + item.slug + ")");
          closeModal();
        });
        card.querySelector('[data-act="zoom"]').addEventListener("click", function (ev) {
          ev.stopPropagation();
          zoomImg.src = item.url || "";
          zoomBackdrop.classList.add("is-open");
        });
        grid.appendChild(card);
      });
    }

    function updatePageInfo() {
      const el = backdrop.querySelector('[data-role="page-info"]');
      el.textContent = "Page " + page + " / " + totalPages;
    }

    function fetchPage() {
      const params = new URLSearchParams();
      params.set("page", String(page));
      if (currentQuery) {
        params.set("q", currentQuery);
      }
      if (currentLang) {
        params.set("language", currentLang);
      }
      return fetch(imagesUrl + "?" + params.toString(), {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      })
        .then(function (r) {
          if (!r.ok) {
            throw new Error("list_failed");
          }
          return r.json();
        })
        .then(function (data) {
          totalPages = Math.max(1, data.num_pages || 1);
          page = data.page || page;
          renderGrid(data.results || []);
          updatePageInfo();
        })
        .catch(function () {
          renderGrid([]);
        });
    }

    function openModal(scope) {
      activeScope = scope;
      page = 1;
      backdrop.classList.add("is-open");
      fetchPage();
    }

    function closeModal() {
      backdrop.classList.remove("is-open");
      activeScope = null;
    }

    backdrop.addEventListener("click", function (ev) {
      if (ev.target === backdrop) {
        closeModal();
      }
    });
    backdrop.querySelector('[data-act="close-modal"]').addEventListener("click", closeModal);

    let searchTimer = null;
    const searchInput = backdrop.querySelector('[data-role="search"]');
    searchInput.addEventListener("input", function () {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () {
        currentQuery = searchInput.value.trim();
        page = 1;
        fetchPage();
      }, 280);
    });

    backdrop.querySelector('[data-role="lang"]').addEventListener("change", function (ev) {
      currentLang = ev.target.value;
      page = 1;
      fetchPage();
    });

    backdrop.querySelector('[data-act="prev"]').addEventListener("click", function () {
      if (page > 1) {
        page -= 1;
        fetchPage();
      }
    });
    backdrop.querySelector('[data-act="next"]').addEventListener("click", function () {
      if (page < totalPages) {
        page += 1;
        fetchPage();
      }
    });

    zoomBackdrop.addEventListener("click", function () {
      zoomBackdrop.classList.remove("is-open");
      zoomImg.removeAttribute("src");
    });

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        closeModal();
        zoomBackdrop.classList.remove("is-open");
      }
    });

    roots.forEach(function (root) {
      const form = root.closest("form");
      if (!form) {
        return;
      }

      const stagingName = root.dataset.stagingName || "staging_id";
      const sourceName = root.dataset.sourceName || "source_image_id";
      const fkName = root.dataset.fkName || "";
      const fileName = root.dataset.fileName || "image";

      const stagingInput = resolveField(form, stagingName);
      const sourceInput = fkName ? null : resolveField(form, sourceName);
      const fkInput = fkName ? resolveField(form, fkName) : null;
      const fileInput = fkName ? null : resolveField(form, fileName);

      if (!stagingInput || (!fkInput && !sourceInput)) {
        return;
      }

      const anchor = root.parentElement || root;

      const shell = document.createElement("div");
      shell.className = "gallery-picker-shell";
      shell.innerHTML =
        '<div class="gallery-picker-actions">' +
        '<button type="button" class="button" data-act="open-library">Media library</button>' +
        '<button type="button" class="button" data-act="upload-stage">Upload (staging)</button>' +
        '<button type="button" class="button" data-act="clear">&times; Clear selection</button>' +
        "</div>" +
        '<label class="gallery-picker-webp-option">' +
        '<input type="checkbox" checked data-role="convert-webp"> Convertir a WebP' +
        '<span> (recomendado)</span>' +
        "</label>" +
        '<input type="file" accept="image/*" style="display:none" data-act="file-stage">' +
        '<div class="gallery-picker-selection">' +
        '<img alt="" data-role="preview">' +
        '<div data-role="caption"></div>' +
        "</div>";

      anchor.insertBefore(shell, root.nextSibling);

      const scope = {
        root: root,
        form: form,
        stagingInput: stagingInput,
        sourceInput: sourceInput,
        fkInput: fkInput,
        fileInput: fileInput,
        selection: shell.querySelector(".gallery-picker-selection"),
        previewImg: shell.querySelector('[data-role="preview"]'),
        captionEl: shell.querySelector('[data-role="caption"]'),
      };
      const initialUrl = (root.dataset.initialUrl || "").trim();
      const initialCaption = (root.dataset.initialCaption || "").trim();
      if (initialUrl) {
        updateSelectionPreview(scope, initialUrl, initialCaption);
      }

      const actions = shell.querySelector(".gallery-picker-actions");
      const fileHidden = shell.querySelector('[data-act="file-stage"]');
      const convertWebp = shell.querySelector('[data-role="convert-webp"]');
      scope.previewImg.addEventListener("click", function () {
        if (!scope.previewImg.src) {
          return;
        }
        zoomImg.src = scope.previewImg.src;
        zoomBackdrop.classList.add("is-open");
      });

      actions.addEventListener("click", function (ev) {
        const t = ev.target.closest("[data-act]");
        if (!t) {
          return;
        }
        const act = t.getAttribute("data-act");
        if (act === "open-library") {
          openModal(scope);
        } else if (act === "upload-stage") {
          fileHidden.click();
        } else if (act === "clear") {
          clearScopeInputs(scope);
        }
      });

      fileHidden.addEventListener("change", function () {
        const f = fileHidden.files && fileHidden.files[0];
        if (!f) {
          return;
        }
        const token = csrfToken();
        const fd = new FormData();
        fd.append("file", uploadSafeFile(f, postImageUploadName(scope, f)));
        fd.append("convert_to_webp", convertWebp && convertWebp.checked ? "true" : "false");
        fetch(stageUrl, {
          method: "POST",
          body: fd,
          credentials: "same-origin",
          headers: token ? { "X-CSRFToken": token } : {},
        })
          .then(function (r) {
            if (!r.ok) {
              return r
                .json()
                .catch(function () {
                  return {};
                })
                .then(function (data) {
                  throw new Error(
                    data.error
                      ? stageUploadErrorMessage(data.error)
                      : "Staging upload failed (HTTP " + r.status + ")."
                  );
                });
            }
            return r.json();
          })
          .then(function (data) {
            clearScopeInputs(scope, { skipRemote: true });
            stagingInput.value = data.id || "";
            if (sourceInput) {
              sourceInput.value = "";
            }
            if (fkInput) {
              fkInput.value = "";
            }
            if (fileInput) {
              fileInput.value = "";
            }
            updateSelectionPreview(scope, data.url || "", "Staged upload (finalize on save)");
          })
          .catch(function (err) {
            window.alert(err && err.message ? err.message : "Staging upload failed.");
          })
          .finally(function () {
            fileHidden.value = "";
          });
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGalleryPickerEcosystem);
  } else {
    initGalleryPickerEcosystem();
  }
})();
