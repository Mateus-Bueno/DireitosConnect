const form = document.getElementById('chat-form');
const input = document.getElementById('mensagem');
const chatBox = document.getElementById('chat-box');
const scrollBtn = document.getElementById('scroll-bottom-btn');

// Função para simular digitação do bot com fade-in
function typeWriter(element, text, delay = 20) {
  let i = 0;
  
  if (text.length > 150) {
      delay -= 15;
  }

  // Ativa o fade-in após pequeno delay
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

// Rola suavemente até o final do chat
function scrollToBottom() {
  chatBox.scrollTo({
    top: chatBox.scrollHeight,
    behavior: 'smooth'
  });
}

// Mostra ou esconde o botão ⬇ dependendo da posição no scroll
function toggleScrollButton() {
  const nearBottom = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 100;
  scrollBtn.style.display = nearBottom ? 'none' : 'flex';
}

// Adiciona uma nova mensagem e atualiza o botão de scroll
function appendMessage(element) {
  chatBox.appendChild(element);
  toggleScrollButton();
}

form.addEventListener('submit', async function (e) {
  e.preventDefault();
  const texto = input.value.trim();
  if (!texto) return;

  // 1) Mensagem do usuário
  const userMsg = document.createElement('div');
  userMsg.className = 'message user';
  userMsg.textContent = texto;
  appendMessage(userMsg);

  input.value = '';
  scrollToBottom();

  // 2) Placeholder do bot
  const botMsg = document.createElement('div');
  botMsg.className = 'message bot';
  appendMessage(botMsg);

  // 3) Requisição ao seu endpoint Flask (/api/chat)
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

// Atualiza botão ao rolar manualmente
chatBox.addEventListener('scroll', toggleScrollButton);
