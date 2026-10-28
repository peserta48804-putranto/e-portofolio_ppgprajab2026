(() => {
  const legacySemesterOneFragments = new Set([
    "implementasi",
    "sp1",
    "sp2",
    "sp3",
    "refleksi",
    "rl-learned",
    "rl-tantangan",
    "rl-feedback",
    "dokumentasi",
  ]);

  if (/\/(?:index\.html)?$/.test(location.pathname) && legacySemesterOneFragments.has(location.hash.slice(1))) {
    location.replace(`semester1.html${location.hash}`);
  }

  if (location.hash) {
    const realignFragment = () => document.querySelector(":target")?.scrollIntoView({ behavior: "instant" });
    window.addEventListener("load", () => {
      if (document.fonts) document.fonts.ready.then(realignFragment);
      else realignFragment();
    }, { once: true });
  }

  document.querySelectorAll("details.mobile-nav").forEach((drawer) => {
    drawer.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && drawer.open) {
        drawer.open = false;
        drawer.querySelector("summary")?.focus();
      }
    });
    drawer.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => {
      drawer.open = false;
    }));
  });

  document.querySelectorAll(".site-nav").forEach((nav) => {
    const fragmentLinks = [...nav.querySelectorAll('a[href^="#"]')];
    const targets = fragmentLinks.map((link) => ({ link, target: document.querySelector(link.hash) })).filter(({ target }) => target);
    const sidebar = nav.closest(".site-sidebar");
    let frame = 0;
    const setCurrentFragment = (hash) => {
      let matched = false;
      const previous = nav.querySelector('[aria-current="location"]');
      let currentLink = null;
      fragmentLinks.forEach((link) => {
        const current = link.hash === hash;
        if (current) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
        if (current) currentLink = link;
        matched ||= current;
      });
      nav.classList.toggle("has-current-section", matched);
      if (currentLink && currentLink !== previous && sidebar) {
        const linkTop = currentLink.offsetTop;
        const linkBottom = linkTop + currentLink.offsetHeight;
        if (linkTop < sidebar.scrollTop) sidebar.scrollTop = linkTop;
        else if (linkBottom > sidebar.scrollTop + sidebar.clientHeight) sidebar.scrollTop = linkBottom - sidebar.clientHeight;
      }
    };
    const updateCurrentSection = () => {
      frame = 0;
      const marker = Math.min(window.innerHeight * 0.2, 96);
      const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;
      const current = atBottom ? targets.at(-1) : targets.filter(({ target }) => target.getBoundingClientRect().top <= marker).at(-1);
      const fallback = nav.querySelector('[aria-current="page"]') ? null : targets[0];
      setCurrentFragment((current || fallback)?.link.hash || "");
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(updateCurrentSection);
    };

    fragmentLinks.forEach((link) => link.addEventListener("click", () => setCurrentFragment(link.hash)));
    sidebar.addEventListener("wheel", (event) => {
      if (!event.deltaY || event.ctrlKey) return;
      event.preventDefault();
      window.scrollBy({ top: event.deltaY, behavior: "instant" });
    }, { passive: false });
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    window.addEventListener("hashchange", schedule);
    schedule();
  });

  document.querySelectorAll("[data-tabs]").forEach((tabs) => {
    const buttons = [...tabs.querySelectorAll("[role=tab]")];
    const panels = [...tabs.querySelectorAll("[role=tabpanel]")];
    const activate = (button) => {
      buttons.forEach((candidate) => candidate.setAttribute("aria-selected", String(candidate === button)));
      panels.forEach((panel) => { panel.hidden = panel.id !== button.getAttribute("aria-controls"); });
    };
    buttons.forEach((button) => button.addEventListener("click", () => activate(button)));
  });

  const semesterOneTabs = [...document.querySelectorAll(".sik-tab")];
  const semesterOnePanels = [...document.querySelectorAll(".sik-panel")];
  window.showSik = (number) => {
    semesterOneTabs.forEach((tab, index) => tab.classList.toggle("active", index === number - 1));
    semesterOnePanels.forEach((panel, index) => panel.classList.toggle("active", index === number - 1));
  };

  window.showRef = (prefix, name, button) => {
    button.parentElement.querySelectorAll(".ref-tab").forEach((tab) => tab.classList.toggle("active", tab === button));
    document.querySelectorAll(".ref-pan").forEach((panel) => panel.classList.toggle("active", panel.id === `${prefix}-${name}`));
  };

  const cycleFromHash = { sp1: 1, sp2: 2, sp3: 3 }[location.hash.slice(1)];
  if (cycleFromHash) window.showSik(cycleFromHash);

  const detailRevealSelector = [
    ".topline",
    ".detail-hero > *",
    ".section-heading",
    ".section > .page-width > .lead",
    ".document-link",
    ".timeline-card",
    ".photo-grid > a",
    ".pending",
    ".section .actions",
    ".portal",
    ".stat-grid > *",
  ].join(",");
  document.querySelectorAll("[data-reveal-page]").forEach((page) => {
    page.querySelectorAll(detailRevealSelector).forEach((item, index) => {
      item.classList.add("rv");
      if (index % 4) item.classList.add(`d${index % 4}`);
    });
  });

  const revealItems = document.querySelectorAll(".rv");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add("in");
    }), { threshold: 0.08 });
    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("in"));
  }

  document.querySelectorAll("[data-catalog]").forEach((catalog) => {
    const items = [...catalog.querySelectorAll("[data-title][data-category]")];
    const buttons = [...catalog.querySelectorAll("[data-filter]")];
    const search = catalog.querySelector("[data-search]");
    const status = catalog.querySelector("[data-status]");
    const reset = catalog.querySelector("[data-reset]");
    let category = "semua";

    const apply = () => {
      const query = search.value.trim().toLocaleLowerCase("id");
      let shown = 0;
      items.forEach((item) => {
        const categoryMatches = category === "semua" || item.dataset.category === category;
        const titleMatches = item.dataset.title.toLocaleLowerCase("id").includes(query);
        item.hidden = !(categoryMatches && titleMatches);
        if (!item.hidden) shown += 1;
      });
      status.textContent = shown ? `${shown} item ditampilkan.` : "Tidak ada item yang cocok.";
      reset.hidden = shown === items.length && !query && category === "semua";
    };

    buttons.forEach((button) => button.addEventListener("click", () => {
      category = button.dataset.filter;
      buttons.forEach((candidate) => candidate.setAttribute("aria-pressed", String(candidate === button)));
      apply();
    }));
    search.addEventListener("input", apply);
    reset.addEventListener("click", () => {
      category = "semua";
      search.value = "";
      buttons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.filter === "semua")));
      apply();
      search.focus();
    });
    apply();
  });
})();
