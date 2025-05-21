const form = document.getElementById('chat-form');
const input = document.getElementById('mensagem');
const chatBox = document.getElementById('chat-box');
const scrollBtn = document.getElementById('scroll-bottom-btn');

function autoResize(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = textarea.scrollHeight + 'px';
}

function scrollToBottom() {
  chatBox.scrollTo({
    top: chatBox.scrollHeight,
    behavior: 'smooth'
  });
}

function toggleScrollButton() {
  const nearBottom = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 100;
  scrollBtn.style.display = nearBottom ? 'none' : 'flex';
}

function appendMessage(element) {
  chatBox.appendChild(element);
  toggleScrollButton();
}

function typeWriter(element, text, delay = 20) {
  let i = 0;
  if (text.length > 150) {
    delay -= 15;
  }

  setTimeout(() => {
    element.classList.add('visible');
  }, 100);

  function type() {
    if (i < text.length) {
      element.textContent += text.charAt(i);
      i++;
      setTimeout(type, delay);
    }
  }
  type();
}

form.addEventListener('submit', async function (e) {
  e.preventDefault();
  const texto = input.value.trim();
  if (!texto) return;

  const userMsg = document.createElement('div');
  userMsg.className = 'message user';
  userMsg.textContent = texto;
  appendMessage(userMsg);

  input.value = '';
  input.style.height = 'auto';
  scrollToBottom();

  const botMsg = document.createElement('div');
  botMsg.className = 'message bot';
  appendMessage(botMsg);

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: texto })
    });

    const data = await resp.json();
    typeWriter(botMsg, data.reply, 20);
  } catch (err) {
    typeWriter(botMsg, 'Desculpe, ocorreu um erro ao obter resposta.', 20);
  }

  scrollToBottom();
});

chatBox.addEventListener('scroll', toggleScrollButton);
