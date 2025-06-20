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

input.addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault(); // impede quebra de linha
    form.requestSubmit(); // dispara envio do form
  } else if (e.key === 'Escape') {
    input.value = '';
    input.blur(); // tira o foco
    input.style.height = 'auto'; // reseta altura
  }
});

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
      body: JSON.stringify({ message: texto, chat_id: CHAT_ID })
    });

    const data = await resp.json();
    typeWriter(botMsg, data.reply, 20);
  } catch (err) {
    typeWriter(botMsg, 'Desculpe, ocorreu um erro ao obter resposta.', 20);
  }

  scrollToBottom();
});


chatBox.addEventListener('scroll', toggleScrollButton);

document.querySelectorAll('.delete-chat-btn').forEach(button => {
  button.addEventListener('click', async (e) => {
    e.stopPropagation();
    const chatId = button.getAttribute('data-chat-id');

    if (confirm('Tem certeza que deseja excluir este chat?')) {
      const response = await fetch('/delete_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId })
      });

      if (response.ok) {
        button.parentElement.remove();
      } else {
        alert('Erro ao excluir o chat.');
      }
    }
  });
});

document.querySelectorAll('.edit-icon').forEach(button => {
  button.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();

    const chatId = button.getAttribute('data-chat-id');
    const chatTitleSpan = button.parentElement.querySelector('.chat-title');
    const currentTitle = chatTitleSpan.innerText;

    // Cria campo de input
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentTitle;
    input.className = 'chat-title-input';

    // Substitui o span pelo input
    button.parentElement.replaceChild(input, chatTitleSpan);
    input.focus();

    // Função para cancelar edição
    const cancelEdit = () => {
      input.replaceWith(chatTitleSpan);
    };

    // Função para salvar edição
    const saveEdit = async () => {
      const newTitle = input.value.trim();
      if (newTitle && newTitle !== currentTitle) {
        const response = await fetch('/edit_chat_title', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id: chatId, new_title: newTitle })
        });

        if (response.ok) {
          chatTitleSpan.innerText = newTitle;
          button.setAttribute('data-current-title', newTitle);
        }
      }
      input.replaceWith(chatTitleSpan);
    };

    input.addEventListener('blur', cancelEdit); // cancela se clicar fora
  });
});