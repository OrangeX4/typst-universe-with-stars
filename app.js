/**
 * app.js – Typst Universe ★
 *
 * Loads packages.json, renders filterable / sortable package cards.
 */

(function () {
  "use strict";

  // -----------------------------------------------------------------------
  // State
  // -----------------------------------------------------------------------
  let allPackages = [];
  let state = {
    search: "",
    sort: "stars",    // "stars" | "last_update" | "last_publish"
    kind: "all",      // "all" | "package" | "template"
    category: "",     // "" = all
  };

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  function formatStars(n) {
    if (n === null || n === undefined) return null;
    return n.toLocaleString();
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatDate(iso) {
    if (!iso) return null;
    try {
      return new Date(iso).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch (err) {
      console.warn("Invalid date string:", iso, err);
      return null;
    }
  }

  // -----------------------------------------------------------------------
  // Filter + sort
  // -----------------------------------------------------------------------

  function applyFilters(packages) {
    let result = packages;

    // Kind
    if (state.kind === "package") {
      result = result.filter((p) => !p.is_template);
    } else if (state.kind === "template") {
      result = result.filter((p) => p.is_template);
    }

    // Category
    if (state.category) {
      result = result.filter(
        (p) =>
          Array.isArray(p.categories) && p.categories.includes(state.category)
      );
    }

    // Search
    const q = state.search.trim().toLowerCase();
    if (q) {
      const terms = q.split(/\s+/);
      result = result.filter((p) => {
        const haystack = [
          p.name || "",
          p.description || "",
          ...(p.keywords || []),
          ...(p.categories || []),
        ]
          .join(" ")
          .toLowerCase();
        return terms.every((t) => haystack.includes(t));
      });
    }

    // Sort
    result = [...result].sort((a, b) => {
      if (state.sort === "stars") {
        // Packages with stars come first; null treated as -1
        const sa = a.stars != null ? a.stars : -1;
        const sb = b.stars != null ? b.stars : -1;
        return sb - sa;
      }
      if (state.sort === "last_update") {
        const da = a.last_update || "";
        const db = b.last_update || "";
        return db < da ? -1 : db > da ? 1 : 0;
      }
      if (state.sort === "last_publish") {
        const da = a.last_publish || "";
        const db = b.last_publish || "";
        return db < da ? -1 : db > da ? 1 : 0;
      }
      return 0;
    });

    return result;
  }

  // -----------------------------------------------------------------------
  // Card rendering
  // -----------------------------------------------------------------------

  function buildCard(pkg) {
    const a = document.createElement("a");
    a.className = "package-card";
    a.href = `https://typst.app/universe/package/${encodeURIComponent(pkg.name)}`;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.setAttribute("role", "listitem");
    a.setAttribute("aria-label", `${pkg.name} – ${pkg.description || "No description"}`);

    let html = "";

    // Thumbnail section (templates)
    if (pkg.is_template) {
      if (pkg.thumbnail) {
        html += `<img
          class="card-thumbnail"
          src="${escapeHtml(pkg.thumbnail)}"
          alt="Preview of ${escapeHtml(pkg.name)} template"
          loading="lazy"
        />`;
      } else {
        html += `<div class="card-thumbnail-placeholder" aria-hidden="true">🖼</div>`;
      }
    }

    // Card body
    html += `<div class="card-body">`;

    // Top row: badge + stars
    const starsFormatted = formatStars(pkg.stars);
    const starsBadge =
      starsFormatted !== null
        ? `<span class="stars-badge" title="${pkg.stars?.toLocaleString()} stars">★ ${starsFormatted}</span>`
        : `<span class="stars-badge no-stars" title="No GitHub stars data">★ —</span>`;

    const kindBadge = pkg.is_template
      ? `<span class="kind-badge template">Template</span>`
      : `<span class="kind-badge package">Package</span>`;

    html += `<div class="card-top">${kindBadge}${starsBadge}</div>`;

    // Name + version
    html += `<div class="card-name-row">
      <h3 class="card-name">${escapeHtml(pkg.name)}</h3>
      <span class="card-version">v${escapeHtml(pkg.version)}</span>
    </div>`;

    // Description
    html += `<p class="card-description">${escapeHtml(pkg.description) || "<em>No description available.</em>"}</p>`;

    // Tags: categories first, then keywords (max 5 total)
    const categories = (pkg.categories || []).map(
      (c) => `<span class="tag category">${escapeHtml(c)}</span>`
    );
    const remaining = Math.max(0, 5 - categories.length);
    const keywords = (pkg.keywords || [])
      .slice(0, remaining)
      .map((k) => `<span class="tag keyword">${escapeHtml(k)}</span>`);

    if (categories.length + keywords.length > 0) {
      html += `<div class="card-tags">${categories.join("")}${keywords.join("")}</div>`;
    }

    html += `</div>`; // .card-body

    a.innerHTML = html;
    return a;
  }

  // -----------------------------------------------------------------------
  // DOM update
  // -----------------------------------------------------------------------

  const grid = document.getElementById("packages-grid");
  const noResults = document.getElementById("no-results");
  const resultInfo = document.getElementById("result-info");

  // Track last rendered column count to avoid unnecessary re-renders on resize
  let lastColCount = 0;

  function getColumnCount() {
    const width = grid.offsetWidth;
    if (width <= 0) return 1;
    const colWidth = window.innerWidth >= 1024 ? 320 : 300;
    const gap = 20;
    return Math.max(1, Math.floor((width + gap) / (colWidth + gap)));
  }

  function render() {
    const filtered = applyFilters(allPackages);

    grid.innerHTML = "";

    if (filtered.length === 0) {
      grid.hidden = true;
      noResults.hidden = false;
    } else {
      noResults.hidden = true;
      grid.hidden = false;

      const numCols = getColumnCount();
      lastColCount = numCols;

      // Create one flex column per masonry column
      const columns = Array.from({ length: numCols }, () => {
        const col = document.createElement("div");
        col.className = "masonry-col";
        return col;
      });

      // Distribute items left-to-right (round-robin) so that the highest-ranked
      // items appear across the top of all columns rather than piling up in col 1.
      filtered.forEach((pkg, i) => {
        columns[i % numCols].appendChild(buildCard(pkg));
      });

      const frag = document.createDocumentFragment();
      columns.forEach((col) => frag.appendChild(col));
      grid.appendChild(frag);
    }

    const total = allPackages.length;
    const shown = filtered.length;
    resultInfo.textContent =
      shown === total
        ? `${total.toLocaleString()} packages`
        : `${shown.toLocaleString()} of ${total.toLocaleString()} packages`;
  }

  // -----------------------------------------------------------------------
  // Category dropdown
  // -----------------------------------------------------------------------

  function populateCategories(packages) {
    const categorySet = new Set();
    packages.forEach((p) => {
      (p.categories || []).forEach((c) => categorySet.add(c));
    });

    const sel = document.getElementById("category-select");
    const sorted = [...categorySet].sort();
    sorted.forEach((cat) => {
      const opt = document.createElement("option");
      opt.value = cat;
      opt.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
      sel.appendChild(opt);
    });
  }

  // -----------------------------------------------------------------------
  // Event wiring
  // -----------------------------------------------------------------------

  // Debounce helper
  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }

  function init() {
    // Sort pills
    document.getElementById("sort-group").addEventListener("click", (e) => {
      const btn = e.target.closest(".pill[data-sort]");
      if (!btn) return;
      document
        .querySelectorAll("#sort-group .pill")
        .forEach((b) => { b.classList.remove("active"); b.setAttribute("aria-pressed", "false"); });
      btn.classList.add("active");
      btn.setAttribute("aria-pressed", "true");
      state.sort = btn.dataset.sort;
      render();
    });

    // Kind pills
    document.getElementById("kind-group").addEventListener("click", (e) => {
      const btn = e.target.closest(".pill[data-kind]");
      if (!btn) return;
      document
        .querySelectorAll("#kind-group .pill")
        .forEach((b) => { b.classList.remove("active"); b.setAttribute("aria-pressed", "false"); });
      btn.classList.add("active");
      btn.setAttribute("aria-pressed", "true");
      state.kind = btn.dataset.kind;
      render();
    });

    // Category select
    document.getElementById("category-select").addEventListener("change", (e) => {
      state.category = e.target.value;
      render();
    });

    // Search input
    const searchInput = document.getElementById("search-input");
    const searchClear = document.getElementById("search-clear");

    const doSearch = debounce(() => {
      state.search = searchInput.value;
      searchClear.hidden = !state.search;
      render();
    }, 200);

    searchInput.addEventListener("input", doSearch);

    searchClear.addEventListener("click", () => {
      searchInput.value = "";
      state.search = "";
      searchClear.hidden = true;
      render();
      searchInput.focus();
    });

    // Re-render when the viewport is resized enough to change column count
    window.addEventListener("resize", debounce(() => {
      if (allPackages.length > 0 && getColumnCount() !== lastColCount) render();
    }, 150));
  }

  // -----------------------------------------------------------------------
  // Data loading
  // -----------------------------------------------------------------------

  function showLoading(show) {
    document.getElementById("loading").hidden = !show;
    grid.hidden = show;
    noResults.hidden = true;
  }

  function showError() {
    document.getElementById("loading").hidden = true;
    document.getElementById("error-state").hidden = false;
  }

  async function loadData() {
    showLoading(true);
    try {
      const resp = await fetch("./packages.json");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      allPackages = Array.isArray(data.packages) ? data.packages : [];

      // Updated time
      if (data.updated_at) {
        const el = document.getElementById("updated-time");
        el.textContent = formatDate(data.updated_at) || data.updated_at;
        el.dateTime = data.updated_at;
      }

      populateCategories(allPackages);
      showLoading(false);
      render();
    } catch (err) {
      console.error("Failed to load packages.json:", err);
      showError();
    }
  }

  // -----------------------------------------------------------------------
  // Bootstrap
  // -----------------------------------------------------------------------
  init();
  loadData();
})();
