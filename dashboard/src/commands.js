export function createCommands(state, actions) {
  const dialog = document.querySelector("#command-dialog"),
    input = document.querySelector("#command-input"),
    results = document.querySelector("#command-results");
  let selected = 0,
    matches = [];
  const commands = [
    ...["operator", "god", "delta"].map((mode) => ({
      label: `${mode === "god" ? "God" : mode[0].toUpperCase() + mode.slice(1)} mode`,
      run: () => actions.setMode(mode),
    })),
    { label: "Present · guided briefing", run: () => actions.present() },
    { label: "Play / pause", run: () => actions.togglePlay() },
    { label: "Reset camera", run: () => actions.home() },
    { label: "Audit scorecard", run: () => actions.setTab("audit") },
    {
      label: "Load scenario data.js",
      run: () => document.querySelector("#file-input").click(),
    },
    ...state.data.objects.map((o) => ({
      label: `Follow ${o.id}`,
      run: () => {
        if (state.mode === "operator") actions.setMode("delta");
        actions.select(o.id);
        actions.follow();
      },
    })),
    ...state.data.events.map((e) => ({
      label: `Jump · ${e.label}`,
      run: () => actions.seek(e.t),
    })),
  ];
  function dynamic(text) {
    let m = text.match(/^jump\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$/i);
    if (m) {
      const [h, min, sec] = m.slice(1).map((v) => Number(v ?? 0));
      if (h > 23 || min > 59 || sec > 59) return [];
      const start = new Date(state.data.scenario.start),
        stamp = Date.UTC(
          start.getUTCFullYear(),
          start.getUTCMonth(),
          start.getUTCDate(),
          h,
          min,
          sec,
        );
      const t = (stamp - start.getTime()) / 1000;
      if (t < 0 || t > state.data.scenario.duration_s)
        return [
          {
            label: "Time is outside this scenario",
            run: () => actions.notify("That UTC time is outside the scenario."),
          },
        ];
      return [
        {
          label: `Jump to ${m[1]}:${m[2]}:${m[3] ?? "00"} UTC`,
          run: () => actions.seek(t),
        },
      ];
    }
    m = text.match(/^dead\s*zones?\s+(\S+)\s+(\d+)\s*m?$/i);
    if (m) {
      const id = Object.keys(state.data.shadow).find(
          (id) => id.toLowerCase() === m[1].toLowerCase(),
        ),
        height = Number(m[2]);
      if (id && height <= 300)
        return [
          {
            label: `Dead zones · ${id} · ${height} m AGL`,
            run: () => {
              if (state.mode === "operator") actions.setMode("delta");
              state.shadowSensor = id;
              state.shadowHeight = height;
              state.shadow = true;
              actions.changed();
            },
          },
        ];
    }
    return [];
  }
  function render() {
    selected = 0;
    const text = input.value.trim().toLowerCase();
    matches = [
      ...dynamic(text),
      ...commands.filter((c) => c.label.toLowerCase().includes(text)),
    ].slice(0, 12);
    results.replaceChildren();
    if (!matches.length) {
      const p = document.createElement("p");
      p.textContent =
        "No matching command. Try “jump 14:02” or “dead zones RF2 40 m”.";
      results.append(p);
    }
    matches.forEach((c, i) => {
      const b = document.createElement("button");
      b.textContent = c.label;
      b.classList.toggle("selected", i === selected);
      b.onclick = () => execute(i);
      results.append(b);
    });
  }
  function execute(index) {
    if (!matches[index]) return;
    dialog.close();
    matches[index].run();
  }
  function open() {
    input.value = "";
    dialog.showModal();
    render();
    input.focus();
  }
  input.oninput = render;
  input.onkeydown = (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      selected =
        (selected + (e.key === "ArrowDown" ? 1 : -1) + matches.length) %
        Math.max(1, matches.length);
      [...results.querySelectorAll("button")].forEach((b, i) =>
        b.classList.toggle("selected", i === selected),
      );
      results
        .querySelectorAll("button")
        [selected]?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      execute(selected);
    }
  };
  document.querySelector("#command-open").onclick = open;
  return { open };
}
