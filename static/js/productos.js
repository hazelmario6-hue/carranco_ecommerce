(() => {
    "use strict";
    const search=document.querySelector("#product-search"),grid=document.querySelector("#catalog-products");if(!search||!grid)return;
    const cards=[...grid.querySelectorAll("[data-product-card]")],chips=[...document.querySelectorAll("[data-filter]")];
    let category=chips.find(chip=>chip.getAttribute("aria-pressed")==="true")?.dataset.filter||"todos";
    const normalize=value=>value.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().trim();
    function render(update=true){
        const query=normalize(search.value);let count=0;
        cards.forEach(card=>{const match=(category==="todos"||card.dataset.category===category)&&normalize(card.dataset.search).includes(query);card.hidden=!match;if(match)count++;});
        grid.hidden=count===0;document.querySelector("#catalog-empty").hidden=count!==0;document.querySelector("#catalog-count").textContent=`${count} ${count===1?"producto":"productos"}`;
        chips.forEach(chip=>chip.setAttribute("aria-pressed",String(chip.dataset.filter===category)));
        if(update){const url=new URL(location.href);if(category==="todos")url.searchParams.delete("categoria");else url.searchParams.set("categoria",category);if(query)url.searchParams.set("q",search.value.trim());else url.searchParams.delete("q");history.replaceState(null,"",url);}
    }
    search.addEventListener("input",()=>render());document.querySelector("#catalog-search-form").addEventListener("submit",event=>{event.preventDefault();render();});
    chips.forEach(chip=>chip.addEventListener("click",()=>{category=chip.dataset.filter;render();}));
    document.querySelector("#reset-catalog").addEventListener("click",event=>{event.preventDefault();category="todos";search.value="";render();search.focus();});
    window.addEventListener("popstate",()=>{const params=new URLSearchParams(location.search);category=params.get("categoria")||"todos";search.value=params.get("q")||"";render(false);});
    render(false);
})();
