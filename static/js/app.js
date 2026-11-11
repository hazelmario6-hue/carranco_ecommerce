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

(() => {
  const drawer=document.querySelector("#app-menu"), opener=document.querySelector("[data-open-menu]");
  if(!drawer||!opener)return;
  opener.addEventListener("click",()=>{drawer.showModal();opener.setAttribute("aria-expanded","true");document.body.classList.add("modal-open");});
  drawer.querySelector("[data-close-menu]").addEventListener("click",()=>drawer.close());
  drawer.addEventListener("click",e=>{if(e.target===drawer){const r=drawer.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)drawer.close();}});
  drawer.addEventListener("close",()=>{opener.setAttribute("aria-expanded","false");document.body.classList.remove("modal-open");opener.focus();});
})();
