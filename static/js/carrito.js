(() => {
    "use strict";
    let queue=Promise.resolve();
    const token=()=>document.querySelector("#csrf-token input")?.value||"";
    function counter(count){document.querySelectorAll("[data-cart-count]").forEach(node=>node.textContent=String(count));document.querySelectorAll(".nav-cart").forEach(node=>node.setAttribute("aria-label",`Carrito, ${count} productos`));}
    counter(Number(document.querySelector("[data-cart-count]")?.textContent||0));
    async function post(url,data){
        const response=await fetch(url,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json","X-CSRFToken":token()},body:JSON.stringify(data),signal:AbortSignal.timeout(15000)});
        const payload=await response.json();
        if(!response.ok||!payload.ok)throw new Error(payload.message||"No fue posible actualizar el carrito.");
        counter(payload.count);return payload;
    }
    document.addEventListener("submit",event=>{
        const form=event.target;if(!form.matches(".cart-add-form"))return;
        event.preventDefault();
        const fields=new FormData(form),button=form.querySelector("button[type=submit]");
        if(button)button.disabled=true;
        const perform=()=>post(document.body.dataset.cartUrl,{producto:Number(fields.get("producto")),cantidad:Number(fields.get("cantidad")),operacion:"add"});
        const task=queue.then(perform);queue=task.catch(()=>{});
        task.then(()=>window.Carranco.notify("Producto agregado al carrito.")).catch(error=>window.Carranco.notify(error.message)).finally(()=>{if(button)button.disabled=false;});
    });
    document.addEventListener("click",event=>{
        const button=event.target.closest("[data-quantity-step]");if(!button)return;
        const form=button.closest("form"),input=form.querySelector("input[name=cantidad]");
        const value=Math.max(1,Math.min(20,Number(input.value)+Number(button.dataset.quantityStep)));input.value=String(value);form.requestSubmit();
    });
    async function importPrevious(){
        let old;
        try{old=JSON.parse(localStorage.getItem("carranco.cart.v1")||"null");}catch{return;}
        if(!Array.isArray(old)||!old.length)return;
        try{
            const payload=await post(document.body.dataset.importUrl,old.map(row=>({id:row.id,quantity:row.quantity})));
            localStorage.removeItem("carranco.cart.v1");
            window.Carranco.notify("Tu selección anterior se transfirió al carrito. "+(payload.warnings||[]).join(" "));
            if(location.pathname===document.body.dataset.cartPage)location.reload();
        }catch(error){window.Carranco.notify("Conservamos tu carrito anterior. "+error.message);}
    }
    queue=queue.then(importPrevious);
})();
