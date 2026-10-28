/* ParkSense dashboard: speaks the small REST/WebSocket contract and remains useful offline. */
(function () {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const total = 20;
  const state = { slots: [], events: [], connected: false, running: true, demo: false, today: 38, cars: 24, bikes: 14 };
  const slotGrid = $("#slot-grid");
  const eventList = $("#event-list");
  const icons = { entry: "↗", exit: "↙", car: "▰", bike: "⌁", system: "⌁" };

  function seedSlots() {
    state.slots = Array.from({ length: total }, (_, i) => ({ id: i + 1, type: i < 8 ? (i % 3 ? "car" : "bike") : "empty" }));
    renderSlots();
  }
  function renderSlots() {
    slotGrid.innerHTML = state.slots.map((slot) => `<div class="slot ${slot.type}" aria-label="Slot ${slot.id} ${slot.type}"><b>${String(slot.id).padStart(2, "0")}</b></div>`).join("");
    const occupied = state.slots.filter((s) => s.type !== "empty").length;
    const percent = Math.round(occupied / total * 100);
    $("#occupied-count").textContent = occupied;
    $("#available-count").textContent = total - occupied;
    $("#total-count").textContent = total;
    $("#occupancy-percent").textContent = `${percent}%`;
    $("#occupancy-ring").style.setProperty("--progress", `${percent}%`);
  }
  function timeAgo(date) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  function addEvent(kind, type, text, detail) {
    state.events.unshift({ kind, type, text, detail, time: new Date() });
    state.events = state.events.slice(0, 7);
    eventList.innerHTML = state.events.map((event) => `<div class="event"><span class="event-icon ${event.type}">${icons[event.kind] || "•"}</span><div><b>${event.text}</b><small>${event.detail || "Edge event received"}</small></div><time>${timeAgo(event.time)}</time></div>`).join("");
  }
  function setConnection(connected, demo) {
    state.connected = connected; state.demo = demo;
    $("#connection-dot").classList.toggle("offline", !connected);
    $("#connection-label").textContent = connected ? "Connected" : "Demo mode";
    $("#last-seen").textContent = connected ? "live" : "local simulation";
    document.body.classList.toggle("offline-mode", demo);
  }
  function updateClock() {
    const text = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    $("#state-updated").textContent = text;
    $("#sensor-sync").textContent = "just now";
  }
  function findAvailable() { return state.slots.find((slot) => slot.type === "empty"); }
  function applyVehicle(action, type, remote) {
    const entering = action === "entry";
    const slot = entering ? findAvailable() : [...state.slots].reverse().find((item) => item.type === type);
    if (entering && !slot) { addEvent("system", "amber", "Garage is at capacity", "No available parking unit"); return; }
    if (!entering && !slot) { addEvent("system", "blue", `No ${type} exit queued`, "Waiting for a matching vehicle"); return; }
    slot.type = entering ? type : "empty";
    if (entering) { state.today += 1; state[type === "car" ? "cars" : "bikes"] += 1; }
    renderSlots();
    $("#today-count").textContent = state.today;
    $("#today-detail").textContent = `${state.cars} cars · ${state.bikes} bikes`;
    animateFlow(action, type);
    addEvent(entering ? "entry" : "exit", type === "car" ? "amber" : "blue", `${type[0].toUpperCase() + type.slice(1)} ${entering ? "entered" : "exited"}`, entering ? `Assigned unit ${String(slot.id).padStart(2, "0")}` : "Gate sensor confirmed");
    if (!remote) sendRest(`/api/vehicle/${action}`, { vehicle_type: type, direction: action });
  }
  function animateFlow(action, type) {
    const vehicle = $("#flow-vehicle");
    vehicle.className = `flow-vehicle ${type}-shape moving`;
    vehicle.style.animationDirection = action === "exit" ? "reverse" : "normal";
    $("#flow-direction").textContent = action === "entry" ? "Entering via east gate" : "Exiting via east gate";
    $("#flow-vehicle-type").textContent = `${type[0].toUpperCase() + type.slice(1)} detected`;
    $("#flow-time").textContent = "just now";
    vehicle.addEventListener("animationend", () => vehicle.classList.remove("moving"), { once: true });
  }
  async function sendRest(path, body) {
    try { await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); } catch (_) { /* WebSocket/demo remains authoritative. */ }
  }
  function normalize(payload) {
    const data = payload.data || payload;
    const incomingSlots = data.slots || data.parking_slots || data.units;
    if (Array.isArray(incomingSlots)) state.slots = incomingSlots.map((slot, index) => {
      if (typeof slot === "string") return { id: index + 1, type: slot === "available" ? "empty" : slot };
      const type = slot.type || slot.vehicle_type || slot.vehicle || (slot.occupied ? "car" : "empty");
      return { id: slot.id || index + 1, type: type === "available" ? "empty" : type };
    });
    if (data.occupancy && typeof data.occupancy === "object") {
      const occupied = Number(data.occupancy.occupied);
      const capacity = Number(data.occupancy.total || data.occupancy.capacity);
      if (Number.isFinite(occupied) && Number.isFinite(capacity)) {
        while (state.slots.length < capacity) state.slots.push({ id: state.slots.length + 1, type: "empty" });
      }
    }
    if (Number.isFinite(data.capacity) && Number.isFinite(data.cars) && Number.isFinite(data.bikes)) {
      const capacity = Number(data.capacity);
      state.slots = Array.from({ length: Math.ceil(capacity) }, (_, index) => {
        const type = index < data.cars ? "car" : index < data.cars + data.bikes ? "bike" : "empty";
        return { id: index + 1, type };
      });
    }
    if (Number.isFinite(data.total)) $("#total-count").textContent = data.total;
    if (Number.isFinite(data.today)) state.today = data.today;
    if (data.event) addEvent(data.event.direction || "system", data.event.vehicle_type === "bike" ? "blue" : "amber", data.event.message || "Vehicle event", data.event.detail);
    if (data.occupancy || incomingSlots) renderSlots();
    updateClock();
  }
  function connect() {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    let socket;
    try { socket = new WebSocket(`${protocol}://${location.host}/ws`); } catch (_) { demoMode(); return; }
    socket.onopen = () => { setConnection(true, false); addEvent("system", "system", "Live connection established", "WebSocket /ws is receiving updates"); };
    socket.onmessage = (message) => { try { normalize(JSON.parse(message.data)); } catch (_) {} };
    socket.onerror = () => { if (!state.connected) demoMode(); };
    socket.onclose = () => { if (state.connected) { setConnection(false, true); addEvent("system", "amber", "Backend disconnected", "Continuing with local simulation"); demoMode(); } };
  }
  async function discoverState() {
    for (const path of ["/api/status", "/api/state", "/status", "/state"]) {
      try { const response = await fetch(path); if (response.ok) { normalize(await response.json()); return true; } } catch (_) {}
    }
    return false;
  }
  function demoMode() {
    setConnection(false, true);
    if (!state.events.length) addEvent("system", "system", "Demo simulation active", "Backend unavailable · local controls enabled");
    window.setInterval(() => {
      if (!state.demo || !state.running || Math.random() > .42) return;
      const type = Math.random() > .35 ? "car" : "bike";
      const entering = Math.random() > .45;
      applyVehicle(entering ? "entry" : "exit", type, true);
    }, 5200);
  }
  function wireControls() {
    $("#start-btn").onclick = () => { state.running = true; $("#start-btn").textContent = "✓ Monitoring active"; sendRest("/api/control/start", {}); addEvent("system", "system", "Monitoring started", "Operator control"); };
    $("#stop-btn").onclick = () => { state.running = false; $("#start-btn").textContent = "▶ Start monitoring"; sendRest("/api/control/stop", {}); addEvent("system", "amber", "Monitoring paused", "Operator control"); };
    document.querySelectorAll("[data-action]").forEach((button) => button.onclick = () => { const [type, action] = button.dataset.action.split("-"); applyVehicle(action, type, false); });
    $("#refresh-btn").onclick = () => { discoverState(); updateClock(); };
    $("#clear-events").onclick = () => { state.events = []; eventList.innerHTML = ""; };
  }
  seedSlots(); wireControls(); updateClock(); discoverState().then((found) => { if (!found) demoMode(); connect(); });
  window.setInterval(updateClock, 1000);
})();
