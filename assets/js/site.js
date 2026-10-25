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
