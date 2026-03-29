(function () {
  const input = document.getElementById("past-jobs-search-input");
  const resultsEl = document.getElementById("past-jobs-live-results");
  if (!input || !resultsEl) return;

  const baseUrl = input.dataset.pastJobsUrl || "";

  function normPath(p) {
    if (!p || p === "/") return p;
    return p.endsWith("/") ? p.slice(0, -1) : p;
  }

  const listPath = normPath(new URL(baseUrl, window.location.origin).pathname);
  let debounceTimer = null;
  const DEBOUNCE_MS = 320;

  function getFilterType() {
    return (input.getAttribute("data-filter-type") || "").trim();
  }

  function syncTypeLinks(q) {
    const qTrim = (q || "").trim();

    const all = document.querySelector(
      '.past-jobs-type-link[title="All types"]'
    );
    const job = document.querySelector(
      '.past-jobs-type-link[title="Driving jobs only"]'
    );
    const shuttle = document.querySelector(
      '.past-jobs-type-link[title="Shuttles only"]'
    );
    const hotel = document.querySelector(
      '.past-jobs-type-link[title="Hotel bookings only"]'
    );

    const uAll = new URL(baseUrl, window.location.origin);
    if (qTrim) uAll.searchParams.set("q", qTrim);
    if (okEl(all)) all.href = uAll.pathname + (uAll.search || "");

    function typeHref(t) {
      const u = new URL(baseUrl, window.location.origin);
      u.searchParams.set("type", t);
      if (qTrim) u.searchParams.set("q", qTrim);
      return u.pathname + u.search;
    }
    if (okEl(job)) job.href = typeHref("job");
    if (okEl(shuttle)) shuttle.href = typeHref("shuttle");
    if (okEl(hotel)) hotel.href = typeHref("hotel");
  }

  function okEl(el) {
    return el && el.tagName === "A";
  }

  function pushListUrl(q, page) {
    const u = new URL(baseUrl, window.location.origin);
    const qTrim = (q || "").trim();
    if (qTrim) u.searchParams.set("q", qTrim);
    else u.searchParams.delete("q");
    const ft = getFilterType();
    if (ft) u.searchParams.set("type", ft);
    else u.searchParams.delete("type");
    if (page && page > 1) u.searchParams.set("page", String(page));
    else u.searchParams.delete("page");
    const next = u.pathname + (u.search ? u.search : "");
    window.history.replaceState(null, "", next);
  }

  function loadPartial(q) {
    const qTrim = (q || "").trim();
    const u = new URL(baseUrl, window.location.origin);
    if (qTrim) u.searchParams.set("q", qTrim);
    const ft = getFilterType();
    if (ft) u.searchParams.set("type", ft);
    u.searchParams.set("_partial", "1");
    u.searchParams.set("page", "1");

    resultsEl.setAttribute("aria-busy", "true");
    fetch(u.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    })
      .then((r) => {
        if (!r.ok) throw new Error(r.statusText);
        return r.text();
      })
      .then((html) => {
        resultsEl.innerHTML = html;
        pushListUrl(qTrim, 1);
        syncTypeLinks(qTrim);
      })
      .catch(() => {
        resultsEl.innerHTML =
          '<p class="past-jobs-error">Could not update results. Try again.</p>';
      })
      .finally(() => {
        resultsEl.removeAttribute("aria-busy");
      });
  }

  function scheduleLoad() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      loadPartial(input.value);
    }, DEBOUNCE_MS);
  }

  input.addEventListener("input", () => {
    scheduleLoad();
  });

  input.addEventListener("search", () => {
    scheduleLoad();
  });

  resultsEl.addEventListener("click", (e) => {
    const a = e.target.closest("a.pagination-btn");
    if (!a || !a.getAttribute("href")) return;
    let u;
    try {
      u = new URL(a.href);
    } catch {
      return;
    }
    if (normPath(u.pathname) !== listPath) return;
    e.preventDefault();
    u.searchParams.set("_partial", "1");
    resultsEl.setAttribute("aria-busy", "true");
    fetch(u.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    })
      .then((r) => {
        if (!r.ok) throw new Error(r.statusText);
        return r.text();
      })
      .then((html) => {
        resultsEl.innerHTML = html;
        const p = parseInt(u.searchParams.get("page") || "1", 10) || 1;
        pushListUrl((input.value || "").trim(), p);
      })
      .catch(() => {
        window.location.href = a.href;
      })
      .finally(() => {
        resultsEl.removeAttribute("aria-busy");
      });
  });

  syncTypeLinks((input.value || "").trim());
})();
