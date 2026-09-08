let bill = null;
let members = ["You", "Friend"];
let selectedFiles = [];
let assignments = {};

const $ = id => document.getElementById(id);
const money = n => `₹${Number(n || 0).toFixed(2)}`;
const escapeHtml = s => String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

function step(n){
  document.querySelectorAll(".step").forEach(x => x.classList.toggle("active", Number(x.dataset.step) === n));
}
function show(panel){
  ["uploadPanel","reviewPanel","assignPanel","resultPanel"].forEach(id => $(id).classList.add("hidden"));
  $(panel).classList.remove("hidden");
}
function renderPreviews(){
  $("previews").innerHTML = "";
  selectedFiles.forEach((f,i)=>{
    const url = URL.createObjectURL(f);
    $("previews").insertAdjacentHTML("beforeend",
      `<div class="preview"><img src="${url}"><span>${i+1}</span></div>`);
  });
  $("extractBtn").disabled = selectedFiles.length === 0;
}
$("files").addEventListener("change", e=>{
  selectedFiles = [...e.target.files].slice(0,2);
  renderPreviews();
});
$("dropzone").addEventListener("dragover", e=>{e.preventDefault();});
$("dropzone").addEventListener("drop", e=>{
  e.preventDefault();
  selectedFiles = [...e.dataTransfer.files].filter(f=>f.type.startsWith("image/")).slice(0,2);
  renderPreviews();
});

$("extractBtn").onclick = async ()=>{
  const fd = new FormData();
  selectedFiles.forEach(f=>fd.append("files",f));
  $("uploadStatus").textContent = "Reading bill… checking line items, taxes and totals.";
  $("extractBtn").disabled = true;
  try{
    const r = await fetch("/api/extract",{method:"POST",body:fd});
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || "Extraction failed");
    bill = data;
    renderReview();
    show("reviewPanel"); step(2);
  }catch(e){$("uploadStatus").textContent = e.message;}
  finally{$("extractBtn").disabled=false;}
};

function renderReview(){
  $("billMeta").innerHTML = `
    <div class="field"><label>RESTAURANT</label><input id="restaurant" value="${escapeHtml(bill.restaurant_name || "")}"></div>
    <div class="field"><label>CURRENCY</label><input id="currency" value="${escapeHtml(bill.currency || "INR")}"></div>`;
  const conf = Number(bill.overall_confidence?.value ?? .5);
  $("confidenceBadge").textContent = `${Math.round(conf*100)}% extraction confidence`;
  $("confidenceBadge").classList.toggle("low",conf<.8);
  renderItems();
  renderCharges();
}
function renderItems(){
  $("itemsBody").innerHTML = bill.items.map((it,i)=>{
    const c = Number(it.confidence?.value ?? .5);
    return `<tr>
      <td><input class="item-input" data-i="${i}" data-k="name" value="${escapeHtml(it.name)}"></td>
      <td><input class="item-input" type="number" step="0.01" data-i="${i}" data-k="quantity" value="${it.quantity}"></td>
      <td><input class="item-input" type="number" step="0.01" data-i="${i}" data-k="unit_price" value="${it.unit_price}"></td>
      <td><input class="item-input" type="number" step="0.01" data-i="${i}" data-k="total_price" value="${it.total_price}"></td>
      <td><span class="confidence ${c<.8?'low':''}">${Math.round(c*100)}%</span></td>
      <td><button class="remove" onclick="removeItem(${i})">×</button></td>
    </tr>`;
  }).join("");
}
function renderCharges(){
  $("charges").innerHTML = [
    ["subtotal","Subtotal",bill.subtotal],
    ["discount","Discount",bill.discount],
    ["service_charge","Service charge",bill.service_charge],
    ["cgst","CGST",bill.cgst],
    ["sgst","SGST",bill.sgst],
    ["other_tax","Other tax",bill.other_tax],
    ["printed_total","Printed total",bill.printed_total ?? 0]
  ].map(([k,l,v])=>`<div class="charge ${k==='printed_total'?'total':''}">
    <label>${l}</label><input id="c_${k}" type="number" step="0.01" value="${Number(v||0).toFixed(2)}">
  </div>`).join("");
}
window.removeItem = i => { bill.items.splice(i,1); renderItems(); };
$("addItem").onclick = ()=>{
  bill.items.push({name:"New item",quantity:1,unit_price:0,total_price:0,confidence:{value:1,note:"Manually added"}});
  renderItems();
};
function syncBill(){
  document.querySelectorAll("[data-i][data-k]").forEach(el=>{
    const i=Number(el.dataset.i), k=el.dataset.k;
    bill.items[i][k] = k==="name" ? el.value : Number(el.value||0);
  });
  bill.restaurant_name=$("restaurant").value;
  bill.currency=$("currency").value;
  ["subtotal","discount","service_charge","cgst","sgst","other_tax","printed_total"].forEach(k=>{
    bill[k]=Number($("c_"+k).value||0);
  });
}
$("backUpload").onclick=()=>{show("uploadPanel");step(1)};
$("toAssign").onclick=()=>{
  syncBill();
  renderMembers(); renderAssignments();
  show("assignPanel");step(3);
};

function renderMembers(){
  $("members").innerHTML=members.map((m,i)=>
    `<span class="member-chip">${escapeHtml(m)} <button onclick="removeMember(${i})">×</button></span>`).join("");
}
window.removeMember=i=>{
  if(members.length<=1)return;
  members.splice(i,1); renderMembers(); renderAssignments();
};
$("addMember").onclick=()=>{
  const name=$("memberName").value.trim();
  if(name && !members.includes(name)){members.push(name);$("memberName").value="";renderMembers();renderAssignments();}
};

function renderAssignments(){
  $("assignmentList").innerHTML=bill.items.map((it,i)=>{
    const current=assignments[i]||{};
    return `<div class="assignment">
      <div class="assignment-top"><b>${escapeHtml(it.name)}</b><span>${money(it.total_price)}</span></div>
      <div class="people-options">${members.map(m=>{
        const p=current[m] ?? 0;
        return `<label class="person-option">
          <input type="checkbox" ${p>0?'checked':''} onchange="togglePerson(${i},'${encodeURIComponent(m)}',this.checked)">
          <span>${escapeHtml(m)}</span>
          <input class="portion" type="number" min="0" step="0.5" value="${p||1}"
             onchange="setPortion(${i},'${encodeURIComponent(m)}',this.value)"
             ${p>0?'':'disabled'}>
        </label>`;
      }).join("")}</div>
      <div class="hint">Portions determine the split of this item. Example: 2 portions vs 1 portion = 66.7% / 33.3%.</div>
    </div>`;
  }).join("");
}
function togglePerson(i,encoded,checked){
  const m=decodeURIComponent(encoded); assignments[i] ||= {};
  if(checked) assignments[i][m]=assignments[i][m]||1;
  else delete assignments[i][m];
  renderAssignments();
}
function setPortion(i,encoded,v){
  const m=decodeURIComponent(encoded); assignments[i] ||= {};
  assignments[i][m]=Math.max(0,Number(v)||0); renderAssignments();
}
$("backReview").onclick=()=>{show("reviewPanel");step(2)};

$("calculate").onclick=async()=>{
  syncBill();
  const out=[];
  for(const [idx,map] of Object.entries(assignments)){
    out.push({item_index:Number(idx),portions:Object.entries(map).map(([member,portions])=>({member,portions}))});
  }
  const unassigned=bill.items.filter((_,i)=>!assignments[i] || Object.values(assignments[i]).reduce((a,b)=>a+b,0)<=0);
  if(unassigned.length){$("assignStatus").textContent="Assign every item before calculating.";return;}
  $("assignStatus").textContent="Calculating…";
  try{
    const r=await fetch("/api/split",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({bill,members,assignments:out})});
    const data=await r.json(); if(!r.ok)throw new Error(data.detail||"Calculation failed");
    renderResults(data); show("resultPanel");step(4);
  }catch(e){$("assignStatus").textContent=e.message;}
};

function renderResults(data){
  $("matchBadge").innerHTML=`<span class="${data.total_matches?'match':'mismatch'}">${data.total_matches?'✓ Totals match':'⚠ Total mismatch'}</span>`;
  $("warning").innerHTML=data.warning?`<div class="warning">⚠ ${escapeHtml(data.warning)}</div>`:"";
  $("results").innerHTML=data.people.map(p=>`
    <div class="person-card">
      <div class="person-head"><b>${escapeHtml(p.member)}</b><span class="amount">${money(p.total)}</span></div>
      <div class="breakdown">
        <div><small>Food</small><strong>${money(p.food_subtotal)}</strong></div>
        <div><small>Discount</small><strong>−${money(p.discount_share)}</strong></div>
        <div><small>Service</small><strong>${money(p.service_charge_share)}</strong></div>
        <div><small>CGST + SGST</small><strong>${money(p.cgst_share+p.sgst_share)}</strong></div>
        <div><small>Other tax</small><strong>${money(p.other_tax_share)}</strong></div>
      </div>
    </div>`).join("");
  $("summary").innerHTML=`<span>Bill total ${money(data.bill_total)}</span><span>People total ${money(data.calculated_total)}</span>`;
}
$("startOver").onclick=()=>{
  bill=null;assignments={};selectedFiles=[];$("files").value="";$("previews").innerHTML="";
  $("uploadStatus").textContent="";show("uploadPanel");step(1);
};
renderMembers();
