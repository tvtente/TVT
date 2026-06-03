(function () {
    function normalizeLocalPath(path) {
        return (path || "").replace(/^\/+/, "");
    }

    function getLanguagePrefix() {
        const lang = document.documentElement.lang || "es";
        return `/${lang}/`;
    }

    function resolveLocalLink(link) {
        const path = normalizeLocalPath(link.getAttribute("data-local-link"));
        if (!path) {
            return "";
        }

        return getLanguagePrefix() + path;
    }

    function hydrateLocalLinks() {
        document.querySelectorAll("[data-local-link]").forEach(function (link) {
            const href = resolveLocalLink(link);
            if (!href) {
                return;
            }

            link.href = href;
        });
    }

    hydrateLocalLinks();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", hydrateLocalLinks);
    } else {
        hydrateLocalLinks();
    }

    document.addEventListener("click", function (event) {
        const link = event.target.closest("[data-local-link]");
        if (!link || event.defaultPrevented) {
            return;
        }

        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }

        const href = resolveLocalLink(link);
        if (!href) {
            return;
        }

        if (!link.getAttribute("href")) {
            event.preventDefault();
            window.location.assign(href);
        }
    }, true);
}());
