const log = document.getElementById('log');
const form = document.getElementById('composer');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');

function appendRow(role, prefixText) {
    const row = document.createElement('div');
    row.className = 'row ' + role;

    const prefix = document.createElement('span');
    prefix.className = 'prefix';
    prefix.textContent = prefixText;

    const content = document.createElement('span');
    content.className = 'content';
    if (role == "") {

    }

    row.appendChild(prefix);
    row.appendChild(content);
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
    return content;
}

function showThinking(contentEl) {
    contentEl.innerHTML = '<span class="thinking"><span></span><span></span><span></span></span>';
}

function setBusy(isBusy) {
    input.disabled = isBusy;
    sendBtn.disabled = isBusy;
}

async function handleSubmit(e) {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    appendRow('user', 'you ~').textContent = text;
    input.value = '';
    setBusy(true);

    const botContent = appendRow('bot', 'qwen3 ~');
    showThinking(botContent);

    try {
        const response = await fetch(
            "http://127.0.0.1:8080/api/chat",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ "prompt": text })
            }
        );

        if (!response.ok) {
            return;
        }

        const res = await response.json();
        if (res.llm_response.name == "none") {
            renderResponse(botContent, "no function registred solve your prompt")
        } else {
            renderResponse(botContent, res)
        }
        console.log(res)
    } catch (err) {
        botContent.parentElement.classList.add('error');
        botContent.textContent = 'error: ' + err.message;
    } finally {
        setBusy(false);
        input.focus();
    }
}


form.addEventListener('submit', handleSubmit);
input.focus();


function renderResponse(contentEl, reply) {
    if (typeof reply === 'string') {
        contentEl.classList.add("failed")
        contentEl.textContent = reply;
    } else {
        renderJsonBlock(contentEl, reply);
    }
}

function renderJsonBlock(contentEl, obj) {
    contentEl.innerHTML = '';
    const jsonText = JSON.stringify(obj, null, 2);

    const block = document.createElement('div');
    block.className = 'json-block';

    const header = document.createElement('div');
    header.className = 'json-header';

    const label = document.createElement('span');
    label.className = 'json-label';
    label.textContent = obj.type || 'json';

    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'copy-btn';
    copyBtn.textContent = 'copy';
    copyBtn.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(jsonText);
            copyBtn.textContent = 'copied';
        } catch (err) {
            copyBtn.textContent = 'failed';
        } finally {
            setTimeout(() => { copyBtn.textContent = 'copy'; }, 1200);
        }
    });

    header.appendChild(label);
    header.appendChild(copyBtn);

    const pre = document.createElement('pre');
    pre.className = 'json-body';
    pre.innerHTML = syntaxHighlight(jsonText);

    block.appendChild(header);
    block.appendChild(pre);
    contentEl.appendChild(block);
}

function syntaxHighlight(jsonText) {
    return jsonText
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
            (match) => {
                let cls = 'jn';
                if (/^"/.test(match)) cls = /:$/.test(match) ? 'jk' : 'jv-str';
                else if (/true|false/.test(match)) cls = 'jb';
                else if (/null/.test(match)) cls = 'jz';
                return '<span class="' + cls + '">' + match + '</span>';
            });
}
