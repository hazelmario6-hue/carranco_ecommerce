(() => {
  "use strict";
  const input=document.querySelector("#codigo"), boxes=[...document.querySelectorAll(".pin-boxes span")];
  function sync(){if(!input)return;input.value=input.value.replace(/[^0-9]/g,"").slice(0,6);boxes.forEach((box,i)=>{box.textContent=input.value[i]||"";box.classList.toggle("filled",!!input.value[i]);});}
  if(input){input.closest(".pin-control").classList.add("enhanced");input.addEventListener("input",sync);sync();}
  const resend=document.querySelector("[data-resend-seconds]"), note=document.querySelector("[data-countdown]");
  if(resend){const until=Date.now()+Number(resend.dataset.resendSeconds)*1000;const tick=()=>{const left=Math.max(0,Math.ceil((until-Date.now())/1000));resend.disabled=left>0;note.textContent=left?`Podrás reenviar en ${left} s.`:"Revisa también la carpeta de spam.";};tick();setInterval(tick,1000);}
  document.querySelectorAll("[data-loading-form]").forEach(form=>form.addEventListener("submit",()=>{const button=form.querySelector("button[type=submit]");button.disabled=true;button.setAttribute("aria-busy","true");button.dataset.originalText=button.textContent;button.textContent=button.dataset.loadingText||"Guardando…";}));
  window.addEventListener("pageshow",()=>document.querySelectorAll("button[data-original-text]").forEach(b=>{b.disabled=false;b.removeAttribute("aria-busy");b.textContent=b.dataset.originalText;}));
})();