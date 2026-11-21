(() => {
  "use strict";
  const body = document.body;
  const pending = new Map();
  let queue = Promise.resolve(), timer, busy = false, uncertain = false;
  const token = () => document.querySelector("#csrf-token input")?.value || "";
  const money = value => "$" + Number(value).toLocaleString("es-MX", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const notify = message => window.Carranco?.notify(message);
  function status(message) { const node = document.querySelector("[data-cart-status]"); if (node) node.textContent = message; }
  function counter(count) {
    document.querySelectorAll("[data-cart-count]").forEach(node => node.textContent = String(count));
    document.querySelectorAll(".nav-cart, .app-bottom-nav a[href='" + body.dataset.cartPage + "']").forEach(node => node.setAttribute("aria-label", `Carrito, ${count} productos`));
  }
  function limits(form) {
    const input = form.querySelector("[name=cantidad]");
    if (!input) return;
    const max = Math.max(0, Number(input.max) || 0);
    const value = Math.min(max, Math.max(1, Math.floor(Number(input.value) || 1)));
    input.value = String(value);
    form.querySelectorAll("[data-quantity-step]").forEach(button => {
      button.disabled = busy || (Number(button.dataset.quantityStep) < 0 ? value <= 1 : value >= max);
    });
    input.disabled = busy || max === 0;
  }
  function checkoutState() {
    document.querySelectorAll("[data-checkout]").forEach(link => {
      const disabled = busy || pending.size > 0 || uncertain;
      link.setAttribute("aria-disabled", String(disabled));
    });
  }
  function setBusy(value) {
    busy = value;
    document.querySelector("[data-cart-view]")?.setAttribute("aria-busy", String(value));
    document.querySelectorAll(".cart-quantity-form button, .cart-remove-form button, .cart-clear-form button").forEach(button => button.disabled = value);
    document.querySelectorAll(".cart-quantity-form").forEach(limits);
    checkoutState();
  }
  function render(data) {
    if (!Array.isArray(data.items)) return;
    counter(data.count);
    const byId = new Map(data.items.map(item => [String(item.id), item]));
    document.querySelectorAll("[data-cart-id]").forEach(row => {
      const id = row.dataset.cartId, line = byId.get(id);
      if (!line) { row.remove(); pending.delete(id); return; }
      row.querySelector("[data-line-subtotal]").textContent = money(line.subtotal);
      const input = row.querySelector("[name=cantidad]");
      input.max = String(line.maximo);
      if (!pending.has(id)) input.value = String(line.cantidad);
      row.querySelector("[data-stock-limit]").textContent = `Máximo disponible: ${line.maximo}`;
      limits(input.form);
    });
    for (const [selector, value] of [["[data-cart-subtotal]", data.subtotal], ["[data-cart-shipping]", data.envio], ["[data-cart-total]", data.total]]) {
      const node = document.querySelector(selector);
      if (node) node.textContent = money(value) + (selector === "[data-cart-total]" ? " MXN" : "");
    }
    const filled = document.querySelector("[data-cart-filled]"), empty = document.querySelector("[data-cart-empty]");
    if (filled) filled.hidden = !data.items.length;
    if (empty) empty.hidden = Boolean(data.items.length);
  }
  async function request(url, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(url, {credentials: "same-origin", cache: "no-store", ...options, signal: controller.signal});
      const data = await response.json();
      if (data.items) render(data);
      if (!response.ok || !data.ok) throw Object.assign(new Error(data.message || "No fue posible actualizar el carrito."), {confirmed: Boolean(data.items), snapshot: data});
      uncertain = false;
      return data;
    } finally { clearTimeout(timeout); }
  }
  function post(url, data) {
    return request(url, {method: "POST", headers: {"Content-Type": "application/json", "X-CSRFToken": token()}, body: JSON.stringify(data)});
  }
  async function recover(error) {
    let message = error.message;
    if (error.snapshot) render(error.snapshot);
    if (!error.confirmed) {
      // A timeout does not mean a POST was cancelled on the server. Never repeat an add automatically.
      uncertain = true;
      message = "No pudimos confirmar la actualización. Revisa tu carrito antes de continuar.";
      try { await request(body.dataset.cartStateUrl); message = "Se recuperó el carrito guardado. Revisa las cantidades antes de continuar."; }
      catch { message = "Sin conexión. Recarga el carrito al recuperarla para confirmar las cantidades."; }
    }
    status(message); notify(message); checkoutState();
  }
  function enqueue(task) {
    const result = queue.then(task);
    queue = result.catch(() => {});
    return result;
  }
  function schedule(form) {
    limits(form);
    const id = form.querySelector("[name=producto]").value;
    pending.set(id, Number(form.querySelector("[name=cantidad]").value));
    clearTimeout(timer);
    status("Actualizando selección…"); checkoutState();
    timer = setTimeout(flush, 300);
  }
  function flush() {
    clearTimeout(timer);
    if (!pending.size || busy) return;
    setBusy(true);
    enqueue(async () => {
      try {
        let message = "Carrito actualizado.";
        for (const [id, quantity] of [...pending]) {
          pending.delete(id);
          const data = await post(body.dataset.cartUrl, {producto: Number(id), cantidad: quantity, operacion: "set"});
          if (data.warnings?.length) message = data.warnings.join(" ");
        }
        status(message);
      } catch (error) { pending.clear(); await recover(error); }
      finally { setBusy(false); }
    });
  }
  document.addEventListener("click", event => {
    const checkout = event.target.closest("[data-checkout]");
    if (checkout && checkout.getAttribute("aria-disabled") === "true") {
      event.preventDefault(); notify(uncertain ? "Confirma las cantidades recargando el carrito." : "Espera a que termine la actualización."); return;
    }
    const button = event.target.closest("[data-quantity-step]");
    if (!button || busy || button.disabled) return;
    const form = button.closest("form"), input = form.querySelector("[name=cantidad]");
    input.value = String(Number(input.value) + Number(button.dataset.quantityStep));
    schedule(form);
  });
  document.addEventListener("input", event => {
    if (event.target.matches(".cart-quantity-form [name=cantidad]") && !busy) schedule(event.target.form);
  });
  document.addEventListener("submit", event => {
    const form = event.target;
    if (form.matches(".cart-quantity-form")) { event.preventDefault(); if (!busy) { schedule(form); flush(); } return; }
    if (!form.matches(".cart-add-form, .cart-remove-form, .cart-clear-form")) return;
    event.preventDefault();
    if (form.dataset.sending === "1" || (busy && !form.matches(".cart-add-form"))) return;
    const fields = new FormData(form), button = form.querySelector("button[type=submit]");
    const action = fields.get("operacion") || "add";
    const payload = action === "clear" ? {operacion: "clear"} : {producto: Number(fields.get("producto")), cantidad: Number(fields.get("cantidad")), operacion: action};
    if (action !== "add") { pending.clear(); clearTimeout(timer); setBusy(true); }
    form.dataset.sending = "1";
    const wasDisabled = button?.disabled;
    if (button) { button.disabled = true; button.setAttribute("aria-busy", "true"); }
    enqueue(async () => {
      try {
        await post(body.dataset.cartUrl, payload);
        const message = action === "add" ? `${form.dataset.productName || "Producto"} agregado al carrito.` : "Carrito actualizado.";
        status(message); notify(message);
      } catch (error) { await recover(error); }
      finally {
        delete form.dataset.sending;
        if (button) { button.disabled = wasDisabled; button.removeAttribute("aria-busy"); }
        if (action !== "add") setBusy(false);
      }
    });
  });
  async function importPrevious() {
    let old;
    try { old = JSON.parse(localStorage.getItem("carranco.cart.v1") || "null"); } catch { return; }
    if (!Array.isArray(old) || !old.length) return;
    try {
      const data = await post(body.dataset.importUrl, old.map(row => ({id: row.id, quantity: row.quantity})));
      localStorage.removeItem("carranco.cart.v1");
      notify("Tu selección anterior se transfirió al carrito. " + (data.warnings || []).join(" "));
      // One-time migration only; quantity changes never reload the page.
      if (location.pathname === body.dataset.cartPage) location.reload();
    } catch (error) { notify("Conservamos tu carrito anterior. " + error.message); }
  }
  counter(Number(document.querySelector("[data-cart-count]")?.textContent || 0));
  document.querySelectorAll(".cart-quantity-form").forEach(limits);
  enqueue(importPrevious);
})();
