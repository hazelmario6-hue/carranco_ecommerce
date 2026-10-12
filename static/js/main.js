(() => {
    "use strict";
    const $ = selector => document.querySelector(selector);
    document.documentElement.classList.add("js");
    const menuButton=$(".menu-toggle"), menu=$("#main-nav");
    function closeMenu() { if(!menuButton||!menu)return; menu.classList.remove("is-open");menuButton.setAttribute("aria-expanded","false");menuButton.setAttribute("aria-label","Abrir menú"); }
    if(menuButton&&menu) {
        menuButton.hidden=false;
        menuButton.addEventListener("click",()=>{const open=menuButton.getAttribute("aria-expanded")!=="true";menu.classList.toggle("is-open",open);menuButton.setAttribute("aria-expanded",String(open));menuButton.setAttribute("aria-label",open?"Cerrar menú":"Abrir menú");});
        document.addEventListener("keydown",event=>{if(event.key==="Escape"&&menu.classList.contains("is-open")){closeMenu();menuButton.focus();}});
        document.addEventListener("click",event=>{if(!event.target.closest(".site-header")||event.target.closest(".main-nav a"))closeMenu();});
        window.matchMedia("(min-width: 901px)").addEventListener("change",closeMenu);
    }
    let timer,returnFocus;
    function notify(message) { const toast=$("#toast");if(!toast)return;clearTimeout(timer);toast.textContent=message;toast.classList.add("is-visible");timer=setTimeout(()=>toast.classList.remove("is-visible"),4500); }
    function showInfo(title,message) { const dialog=$("#info-dialog");if(!dialog)return;returnFocus=document.activeElement;$("#info-title").textContent=title;$("#info-message").textContent=message;dialog.showModal();document.body.classList.add("modal-open"); }
    const help={envios:["Envíos","Contacta al equipo para coordinar la entrega y consultar sus condiciones."],pagos:["Métodos de pago","La pasarela captura la tarjeta en su propia página. El total a pagar se muestra y acepta en el checkout. Un pedido solo figura pagado tras la verificación del servidor."]};
    document.addEventListener("click",event=>{
        const control=event.target.closest("button,a");if(!control)return;
        if("closeDialog" in control.dataset){control.closest("dialog")?.close();return;}
        if("whatsapp" in control.dataset){showInfo("Asistente Carranco","El asistente aún no está conectado a WhatsApp. Puedes dejar tu consulta en la página de Contacto; esta ventana no envía mensajes.");return;}
        if("social" in control.dataset){showInfo(control.dataset.social+"","Este perfil aún no está conectado.");return;}
        if("help" in control.dataset&&help[control.dataset.help])showInfo(...help[control.dataset.help]);
    });
    document.querySelectorAll("dialog").forEach(dialog=>{
        dialog.addEventListener("close",()=>{document.body.classList.remove("modal-open");if(returnFocus?.isConnected)returnFocus.focus();});
        dialog.addEventListener("click",event=>{if(event.target!==dialog)return;const bounds=dialog.getBoundingClientRect();if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)dialog.close();});
    });
    function imageFallback(image){
        if(!(image instanceof HTMLImageElement)||image.hasAttribute("data-gallery-main"))return;
        if(image.hasAttribute("data-brand-logo")){image.hidden=true;if(image.nextElementSibling)image.nextElementSibling.hidden=false;return;}
        const fallback=document.createElement("span");fallback.className="image-unavailable";fallback.textContent="Imagen no disponible";fallback.setAttribute("role","img");fallback.setAttribute("aria-label",image.alt);image.replaceWith(fallback);
    }
    document.addEventListener("error",event=>imageFallback(event.target),true);
    document.querySelectorAll("img").forEach(image=>{if(image.complete&&image.naturalWidth===0)imageFallback(image);});
    window.Carranco=Object.freeze({notify,showInfo});
})();
