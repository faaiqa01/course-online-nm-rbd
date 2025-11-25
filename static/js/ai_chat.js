(function () {
  const form = document.getElementById('ai-chat-form');
  if (!form) {
    return;
  }

  const input = document.getElementById('ai-chat-input');
  const log = document.getElementById('ai-chat-log');
  const status = document.getElementById('ai-chat-status');
  const sendButton = form.querySelector('button[type="submit"]');

  function setStatus(message) {
    if (!status) {
      return;
    }
    status.textContent = message || '';
  }

  function appendMessage(role, text) {
    const wrapper = document.createElement('div');
    wrapper.className = `ai-chat-message ai-chat-${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'ai-chat-bubble';

    // Render Markdown untuk bot, plain text untuk user
    if (role === 'bot' && typeof marked !== 'undefined') {
      // Configure marked untuk keamanan
      marked.setOptions({
        breaks: true,  // Convert line breaks to <br>
        gfm: true,     // GitHub Flavored Markdown
        headerIds: false,  // Disable header IDs untuk keamanan
        mangle: false  // Disable email mangling
      });

      // Render Markdown jadi HTML
      const htmlContent = marked.parse(text);
      bubble.innerHTML = htmlContent;
    } else {
      // User message tetap plain text
      bubble.textContent = text;
    }

    wrapper.appendChild(bubble);
    log.appendChild(wrapper);
    log.scrollTop = log.scrollHeight;
  }

  async function sendMessage(message) {
    try {
      const response = await fetch('/api/ai-chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.error || 'Permintaan gagal diproses.';
        appendMessage('bot', errorMessage);
        return;
      }

      const data = await response.json();
      appendMessage('bot', data.reply || 'Maaf, tidak ada jawaban yang tersedia.');
    } catch (error) {
      appendMessage('bot', 'Terjadi kesalahan koneksi. Coba lagi nanti.');
    }
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = (input.value || '').trim();
    if (!message) {
      setStatus('Pesan tidak boleh kosong.');
      return;
    }

    appendMessage('user', message);
    input.value = '';
    setStatus('Menghubungi asisten...');
    input.disabled = true;
    if (sendButton) {
      sendButton.disabled = true;
    }

    await sendMessage(message);

    setStatus('');
    input.disabled = false;
    input.focus();
    if (sendButton) {
      sendButton.disabled = false;
    }
  });
})();