(() => {
  "use strict";
  // Hide bottom navigation while the software keyboard is using the viewport.
  const viewport = window.visualViewport;
  function updateKeyboard() {
    const field = document.activeElement;
    const typing = field && /^(INPUT|TEXTAREA|SELECT)$/.test(field.tagName);
    document.body.classList.toggle("keyboard-open", Boolean(typing && viewport && window.innerHeight - viewport.height > 120));
  }
  viewport?.addEventListener("resize", updateKeyboard);
  document.addEventListener("focusin", updateKeyboard);
  document.addEventListener("focusout", () => setTimeout(updateKeyboard, 100));
})();
