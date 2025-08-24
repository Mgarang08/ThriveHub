async function callBackend(message){
  const res = await fetch("https://thrivehub-a85v.onrender.com/api/anxiety-copilot", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ user_id: "demo", message })
  });
  return res.json();
}

async function sendText(){
  const t = text.value.trim();
  if (!t) return;
  text.value = '';
  pushUser(t);

  await new Promise(r => setTimeout(r, 250));

  let replyObj;
  try {
    const data = await callBackend(t);
    replyObj = { text: data.reply };
  } catch (e) {
    console.warn("Backend failed, using fallback:", e);
    replyObj = ruleBasedReply(t);
  }

  pushAssistant(replyObj.text);
  if (replyObj.suggest && replyObj.suggest.length){
    pushAssistant(JSON.stringify({ _suggest: replyObj.suggest }));
  }
}