const form = document.getElementById('chat-form');
const input = document.getElementById('mensagem');
const chatBox = document.getElementById('chat-box');
const scrollBtn = document.getElementById('scroll-bottom-btn');

let CHAT_ID = typeof window.CHAT_ID !== 'undefined' ? window.CHAT_ID : null;

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
  return new Promise((resolve) => {
    let i = 0;
    if (text && text.length > 150) {
      delay = Math.max(5, delay - 15);
    }

    setTimeout(() => {
      element.classList.add('visible');
    }, 100);

    function type() {
      if (i < (text || '').length) {
        element.textContent += text.charAt(i);
        i++;
        setTimeout(type, delay);
      } else {
        resolve();
      }
    }
    type();
  });
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

  const boasVindas = document.getElementById('mensagem-boas-vindas');
  if (boasVindas) {
    boasVindas.remove();
  }

  input.value = '';
  input.style.height = 'auto';
  scrollToBottom();

  const botMsg = document.createElement('div');
  botMsg.className = 'message bot';
  appendMessage(botMsg);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s

  // trava input enquanto "digita"
  form.querySelector('button[type="submit"]')?.setAttribute('disabled', 'true');
  input.disabled = true;

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({ message: texto, chat_id: CHAT_ID })
    });

    clearTimeout(timeoutId);

    if (!resp.ok) {
      throw new Error(`Erro HTTP ${resp.status}`);
    }

    const contentType = resp.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      throw new Error("Resposta não é JSON válida");
    }

    const data = await resp.json();

    // Atualiza CHAT_ID e URL sem recarregar
    if (data.chat_id && (CHAT_ID === null || CHAT_ID !== data.chat_id)) {
      CHAT_ID = data.chat_id;
      const cleanUrl = `/chat/${CHAT_ID}`.replace(/\/+$/, '').replace(/\?$/, '');
      window.history.replaceState({}, '', cleanUrl);
    }

    // Adiciona o novo chat à sidebar se ainda não existir
    if (!document.querySelector(`[data-chat-id="${CHAT_ID}"]`)) {
      addChatToSidebar(CHAT_ID, data.titulo || "Nova conversa");
    }

    // Digita a resposta da Lia
    if (data.reply) {
      await typeWriter(botMsg, data.reply, 20);
    } else {
      botMsg.textContent = 'Sem resposta.';
    }

    // Só depois começa a digitar a recomendação
    if (data.recommendation) {
      const recMsg = document.createElement('div');
      recMsg.className = 'message bot';
      appendMessage(recMsg);
      await typeWriter(recMsg, data.recommendation, 20);
    }

  } catch (err) {
    console.error('Erro ao buscar resposta:', err);
    botMsg.textContent = 'Desculpe, ocorreu um erro ao obter resposta.';
  } finally {
    form.querySelector('button[type="submit"]')?.removeAttribute('disabled');
    input.disabled = false;
    input.focus();
    scrollToBottom();
  }
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

function addChatToSidebar(chatId, titulo) {
  const sidebar = document.getElementById('sidebar');
  const noChatsMsg = document.getElementById('no-chats-msg');
  if (noChatsMsg) {
    noChatsMsg.remove();
  }

  const wrapper = document.createElement('div');
  wrapper.className = 'conversation-wrapper';

  const link = document.createElement('a');
  link.href = `/chat/${chatId}`;
  link.className = 'conversation';
  link.setAttribute('data-chat-id', chatId);

  const span = document.createElement('span');
  span.className = 'chat-title';
  span.innerText = titulo;

  const editIcon = document.createElement('span');
  editIcon.className = 'edit-icon';
  editIcon.setAttribute('data-chat-id', chatId);
  editIcon.setAttribute('data-current-title', titulo);
  editIcon.innerText = '✎';

  link.appendChild(span);
  link.appendChild(editIcon);

  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'delete-chat-btn';
  deleteBtn.setAttribute('data-chat-id', chatId);
  deleteBtn.innerText = '×';

  wrapper.appendChild(link);
  wrapper.appendChild(deleteBtn);

  sidebar.insertBefore(wrapper, sidebar.querySelector('form'));

  attachChatEventListeners(wrapper);
}

function attachChatEventListeners(wrapper) {
  const deleteBtn = wrapper.querySelector('.delete-chat-btn');
  const editIcon = wrapper.querySelector('.edit-icon');

  if (deleteBtn) {
    deleteBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const chatId = deleteBtn.getAttribute('data-chat-id');

      if (confirm('Tem certeza que deseja excluir este chat?')) {
        const response = await fetch('/delete_chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id: chatId })
        });

        if (response.ok) {
          wrapper.remove();
        } else {
          alert('Erro ao excluir o chat.');
        }
      }
    });
  }

  if (editIcon) {
    editIcon.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();

      const chatId = editIcon.getAttribute('data-chat-id');
      const chatTitleSpan = editIcon.parentElement.querySelector('.chat-title');
      const currentTitle = chatTitleSpan.innerText;

      const input = document.createElement('input');
      input.type = 'text';
      input.value = currentTitle;
      input.className = 'chat-title-input';

      editIcon.parentElement.replaceChild(input, chatTitleSpan);
      input.focus();

      const cancelEdit = () => {
        input.replaceWith(chatTitleSpan);
      };

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
            editIcon.setAttribute('data-current-title', newTitle);
          }
        }
        input.replaceWith(chatTitleSpan);
      };

      input.addEventListener('blur', cancelEdit);
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') saveEdit();
        else if (e.key === 'Escape') cancelEdit();
      });
    });
  }
}
