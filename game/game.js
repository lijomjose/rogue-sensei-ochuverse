"use strict";
const $ = id => document.getElementById(id);
const starter = `void charge(int *target)\n{\n    // Send 20 more energy to the beacon.\n    // Write your spell here.\n}\n`;
const scenes = [
  {title:"A sky you do not remember", copy:["Cold stone. A sky split by a fading violet scar. You sit up beside the wreckage of something that might once have carried you.","Your name will not come. Neither will the memory of falling.","A small beacon flickers ahead. Beneath it, a cracked console waits."], button:"Inspect the beacon →"},
  {title:"A destination, not a charge", copy:["The console wakes beneath your hand. Its instructions are strangely familiar, even though nothing else is.","“Energy needs a destination. The control pointer holds the address of the beacon’s charge.”", "Your spell receives that address as target. Restore the beacon by increasing the integer there by 20."], button:null},
  {title:"Someone beyond the light", copy:["The beacon brightens. For a moment, the fractured arch behind it shimmers. Then the glow steadies into a narrow path through the ruins.","A voice travels out of the dark: “Good. You changed what it pointed to.”", "A figure approaches, carrying a battered satchel. Something about him feels familiar. You cannot yet say why."], button:"Follow the voice →"},
  {title:"The first path is open", copy:["He stops before you, relief almost hidden behind a crooked smile. “Let’s get you somewhere safe. Questions can walk with us.”", "Far above, a faint signal strikes the broken arch and dissolves. Whoever is calling cannot reach this world yet.","End of the opening preview. Next: meet Rogue Sensei, rebuild the shelter’s memory, and discover why Pointerra’s paths are sealed."], button:null}
];
let state = {stage:0, source:starter};
let ready = false, busy = false, saveTimer;
let saving = Promise.resolve();
const token = location.pathname.split("/")[1];
async function post(path, payload) {
  const response = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json", "X-Ochu-Session":token}, body:JSON.stringify(payload)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "The local game could not respond.");
  return result;
}
function save() {
  const snapshot = {...state};
  saving = saving.catch(()=>{}).then(()=>post("api/save", snapshot));
  return saving.then(()=>{$("save-status").textContent="Journal saved on this computer.";}, error=>{$("save-status").textContent="Saving failed. Keep this window open and copy your spell."; throw error;});
}
function render() {
  const scene = scenes[state.stage];
  $("story-title").textContent = scene.title;
  $("story-copy").replaceChildren(...scene.copy.map(text=>{const p=document.createElement("p");p.textContent=text;return p;}));
  $("progress").textContent = `${Math.min(state.stage + 1,3).toString().padStart(2,"0")} / 03`;
  $("continue").hidden = !scene.button;
  $("continue").textContent = scene.button || "";
  $("run").disabled = !ready || state.stage === 0 || busy;
  $("code").disabled = !ready || state.stage === 0 || busy;
  $("lamp").classList.toggle("lit", state.stage >= 2);
  $("scene-status").textContent = state.stage >= 2 ? "BEACON RESTORED" : "BEACON OFFLINE";
}
function cell(title, lines) {
  const element=document.createElement("div");element.className="cell";
  const strong=document.createElement("strong");strong.textContent=title;element.append(strong);
  for (const [label,value] of lines) {const span=document.createElement("span");span.textContent=label;const code=document.createElement("code");code.textContent=String(value);element.append(span,code);}
  return element;
}
function showMemory(result) {
  const caseResult=result.cases?.find(c=>c.initial===40) || result.cases?.[0];
  if (!caseResult) return;
  const before=caseResult.events.find(e=>e.event==="lamp" && e.phase==="before");
  const after=caseResult.events.find(e=>e.event==="lamp" && e.phase==="after");
  if (!before) return;
  const arrow=document.createElement("div");arrow.className="arrow";arrow.textContent="↓ points to ↓";
  $("memory-view").replaceChildren(
    cell("Caller’s pointer", [["Pointer’s own address",before.pointer_address],["Address stored inside",before.stored_address]]),
    arrow,
    cell("Beacon’s charge", [["Integer’s address",before.object_address],["Charge before → after",`${before.value} → ${after?.value ?? "execution stopped"}`]])
  );
}
$("continue").onclick=async()=>{state.stage=Math.min(3,state.stage+1);render();$("output").textContent="Console ready. Write your spell and cast it.";try{await save();}catch{}};
$("hint").onclick=()=>{$("hint-copy").hidden=!$("hint-copy").hidden;};
$("code").oninput=()=>{state.source=$("code").value;$("save-status").textContent="Saving your spell…";clearTimeout(saveTimer);saveTimer=setTimeout(()=>save().catch(()=>{}),400);};
$("run").onclick=async()=>{
  if (busy) return;
  busy=true;render();clearTimeout(saveTimer);state.source=$("code").value;
  $("output").textContent="Compiling your spell…";
  try {
    try {await save();} catch {} // Allow playing when storage is unavailable.
    const result=await post("api/run", {source:state.source});
    showMemory(result);
    if (result.status==="passed") {
      if (state.stage<2) state.stage=2;
      $("output").textContent="Beacon restored. Your spell changed the original charge in all three trials.\n"+result.cases.map(c=>`${c.initial} → ${c.observed}  ✓`).join("\n");
      if (!result.sanitizers) $("output").textContent+="\nCompiler compatibility mode: memory diagnostics unavailable.";
      try {await save();}catch{}
    } else {
      const lines=[`Spell result: ${result.status}`];
      if(result.compile_diagnostics)lines.push(result.compile_diagnostics);
      for (const c of result.cases || []) {lines.push(`Start ${c.initial}: expected ${c.expected}, observed ${c.observed ?? "no final value"} (${c.status})`);if(c.runtime_diagnostics)lines.push(c.runtime_diagnostics);}
      if(result.cases?.some(c=>c.status==="wrong_result")) lines.push("Check whether you changed the integer at the address, rather than the pointer itself.");
      $("output").textContent=lines.join("\n");
    }
  } catch(error){$("output").textContent=error.message+"\nIf the launcher closed, start it again.";}
  finally{busy=false;render();}
};
$("reset").onclick=async()=>{if(busy || !confirm("Restart this opening and clear your saved spell?"))return;state={stage:0,source:starter};$("code").value=starter;$("memory-view").textContent="Awaiting a spell.";$("output").textContent="Inspect the beacon to unlock its console.";render();try{await save();}catch{}};
async function init(){
  try {
    const response=await fetch("api/save");
    if(!response.ok)throw new Error("Could not load your journal.");
    const saved=await response.json();
    if(saved.source!==undefined)state=saved;
    $("save-status").textContent="Journal loaded. Everything stays on this computer.";
  }catch(error){$("save-status").textContent=error.message;}
  ready=true;$("code").value=state.source;render();
  if(state.stage>0)$("output").textContent="Console ready. Write your spell and cast it.";
}
render();init();
