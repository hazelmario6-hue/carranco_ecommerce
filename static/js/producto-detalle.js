(() => {
    "use strict";
    const image=document.querySelector("#main-product-image"),fallback=document.querySelector("#gallery-error"),thumbs=[...document.querySelectorAll("[data-photo-src]")];
    thumbs.forEach(button=>button.addEventListener("click",()=>{image.hidden=false;fallback.hidden=true;image.src=button.dataset.photoSrc;image.alt=button.dataset.photoAlt;document.querySelector("#gallery-caption").textContent=button.dataset.photoCaption;thumbs.forEach(other=>other.setAttribute("aria-pressed",String(other===button)));}));
    image.addEventListener("error",()=>{image.hidden=true;fallback.hidden=false;fallback.setAttribute("role","img");fallback.setAttribute("aria-label",image.alt);});
    image.addEventListener("load",()=>{image.hidden=false;fallback.hidden=true;});
    if(image.complete&&image.naturalWidth===0){image.hidden=true;fallback.hidden=false;}
    const quantity=document.querySelector("#product-quantity"),minus=document.querySelector("#quantity-minus"),plus=document.querySelector("#quantity-plus");
    function set(value){quantity.value=String(Math.min(Number(quantity.max),Math.max(1,Math.floor(Number(value)||1))));minus.disabled=Number(quantity.value)<=1;plus.disabled=Number(quantity.value)>=Number(quantity.max);}
    minus.addEventListener("click",()=>set(Number(quantity.value)-1));plus.addEventListener("click",()=>set(Number(quantity.value)+1));quantity.addEventListener("change",()=>set(quantity.value));set(1);
})();
