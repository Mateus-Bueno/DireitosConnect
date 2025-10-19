import os
import time
import random
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_mysqldb import MySQL
from dotenv import load_dotenv
from openai import OpenAI
import MySQLdb.cursors
import bcrypt

# Carrega variáveis do .env
load_dotenv(dotenv_path='/home/DireitosConnect/mysite/.env')

# Configuração da OpenAI
client = OpenAI(api_key=os.getenv('openai_key'))

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'Direito')

# Configuração do MySQL
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
# (Opcional) garantir unicode completo:
# app.config['MYSQL_CHARSET'] = 'utf8mb4'
# app.config['MYSQL_USE_UNICODE'] = True

mysql = MySQL(app)

def identificar_area_juridica(resposta):
    areas = [
        'Direito Penal', 'Direito Civil', 'Direito Trabalhista',
        'Direito do Consumidor', 'Direito Tributário', 'Direito de Família',
        'Direito Previdenciário', 'Direito Ambiental'
    ]
    for area in areas:
        if area.lower() in resposta.lower():
            return area
    return None

def recomendar_advogado_por_area(area):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        like = f"%{area}%"
        cursor.execute("""
            SELECT nome, telefone, horario_trabalho, especialidade
            FROM advogados
            WHERE LOWER(especialidade) LIKE LOWER(%s)
            ORDER BY RAND() LIMIT 1
        """, (like,))
        row = cursor.fetchone()

        if not row:
            mapas = {
                'Direito do Consumidor': ['Consumidor', 'Defesa do Consumidor'],
                'Direito Trabalhista': ['Trabalhista', 'Trabalho'],
                'Direito Civil': ['Civil'],
                'Direito Penal': ['Penal', 'Criminal'],
                'Direito de Família': ['Família', 'Familia'],
                'Direito Previdenciário': ['Previdenciário', 'Previdenciario', 'INSS'],
                'Direito Tributário': ['Tributário', 'Tributario', 'Fiscal'],
                'Direito Ambiental': ['Ambiental', 'Meio Ambiente'],
            }
            termos = mapas.get(area, [])
            if termos:
                like_terms = tuple(f"%{t}%" for t in termos)
                where = " OR ".join(["LOWER(especialidade) LIKE LOWER(%s)"] * len(termos))
                cursor.execute(f"""
                    SELECT nome, telefone, horario_trabalho, especialidade
                    FROM advogados
                    WHERE {where}
                    ORDER BY RAND() LIMIT 1
                """, like_terms)
                row = cursor.fetchone()

        if not row:
            return None

        nome = row['nome']
        tel = row['telefone']
        horario = row.get('horario_trabalho') or 'Horário não informado'
        espec = row.get('especialidade') or area

        cartao = (
            "*Recomendação de Advogado(a)**\n"
            f"**Especialidade:** {espec}\n"
            f"**Nome:** {nome}\n"
            f"**Telefone:** {tel}\n"
            f"**Atendimento:** {horario}"
        )
        return cartao

    except Exception as e:
        print("Erro ao recomendar advogado:", e)
        return None

def obter_resposta_openai(texto, chat_id=None):
    try:
        if 'chat_history' not in session:
            session['chat_history'] = []

            prompt = """
            Você é uma assistente chamada Lia, especializada em assuntos jurídicos. Seu papel é ajudar os clientes a compreenderem,
            de forma objetiva e acessível, dúvidas relacionadas a situações jurídicas.

            Regras:
            - Use linguagem simples e respostas com até 4 parágrafos.
            - Não ofereça conclusões legais definitivas; oriente e esclareça.
            - Sempre que possível, identifique explicitamente a área do direito, por exemplo:
              "Área: Direito do Consumidor" (ou Penal, Civil, Trabalhista, Tributário, Família, Previdenciário, Ambiental).
            - Caso não seja possível definir com segurança a área jurídica, peça mais detalhes.
            """

            # Carrega histórico, se houver
            if chat_id:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute(
                    "SELECT remetente, conteudo FROM mensagens WHERE chat_id = %s ORDER BY enviada_em LIMIT 6",
                    (chat_id,)
                )
                mensagens = cursor.fetchall()

                for m in mensagens:
                    session['chat_history'].append({
                        "role": "user" if m['remetente'].strip().lower() == "usuario" else "assistant",
                        "content": m['conteudo']
                    })

            session['chat_history'].insert(0, {"role": "system", "content": prompt})

        # Adiciona nova pergunta
        session['chat_history'].append({"role": "user", "content": texto})

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=session['chat_history']
        )

        resposta = completion.choices[0].message.content
        session['chat_history'].append({"role": "assistant", "content": resposta})

        # Salva no banco se for chat persistente
        if chat_id:
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO mensagens (chat_id, remetente, conteudo) VALUES (%s, %s, %s)",
                           (chat_id, 'usuario', texto))
            cursor.execute("INSERT INTO mensagens (chat_id, remetente, conteudo) VALUES (%s, %s, %s)",
                           (chat_id, 'ia', resposta))
            mysql.connection.commit()
            cursor.close()

        return resposta

    except Exception as e:
        print("Erro OpenAI:", e)
        time.sleep(10)
        return "Desculpe, estou com dificuldades técnicas no momento. Por favor, tente mais tarde."

@app.route('/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha   = request.form['senha']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(senha.encode('utf-8'), user['senha'].encode('utf-8')):
            session['usuario'] = usuario
            return redirect(url_for('chat'))
        elif user:
            msg = 'Senha incorreta.'
        else:
            msg = 'Usuário não encontrado.'

    return render_template('login.html', msg=msg)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    msg = ''
    if request.method == 'POST':
        nome      = request.form['nome']
        usuario   = request.form['usuario']
        email     = request.form['email']
        telefone  = request.form['telefone']
        senha     = request.form['senha']
        confirmar = request.form['Confirmar Senha']

        if senha != confirmar:
            msg = 'As senhas não coincidem!'
        else:
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor = mysql.connection.cursor()

            cursor.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
            conta_email = cursor.fetchone()

            cursor.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
            conta_usuario = cursor.fetchone()

            if conta_email:
                msg = 'E-mail já cadastrado!'
            elif conta_usuario:
                msg = 'Nome de usuário já está em uso!'
            else:
                cursor.execute(
                    'INSERT INTO usuarios (nome, usuario, email, telefone, senha) VALUES (%s, %s, %s, %s, %s)',
                    (nome, usuario, email, telefone, senha_hash)
                )
                mysql.connection.commit()
                return redirect(url_for('login'))

    return render_template('cadastro.html', msg=msg)

@app.route('/chat')
def chat():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    session.pop('chat_id', None)  # limpa qualquer chat antigo

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (session['usuario'],))
    user = cursor.fetchone()

    cursor.execute("SELECT id, titulo FROM chats WHERE usuario_id = %s ORDER BY criado_em DESC", (user['id'],))
    chats = cursor.fetchall()

    return render_template('chat.html', chats=chats, mensagens=[], chat_id=None)

@app.route('/chat/<int:chat_id>')
def abrir_chat(chat_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    session['chat_id'] = chat_id
    session.pop('chat_history', None)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Mensagens do chat atual
    cursor.execute("SELECT remetente, conteudo FROM mensagens WHERE chat_id = %s ORDER BY enviada_em", (chat_id,))
    mensagens = cursor.fetchall()

    # Chats do usuário
    cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (session['usuario'],))
    user = cursor.fetchone()
    cursor.execute("SELECT id, titulo FROM chats WHERE usuario_id = %s ORDER BY criado_em DESC", (user['id'],))
    chats = cursor.fetchall()

    return render_template('chat.html', mensagens=mensagens, chats=chats, chat_id=chat_id)

@app.route('/chat/novo', methods=['POST'])
def novo_chat():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    titulo = request.form.get('titulo', 'Novo Chat')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (session['usuario'],))
    user = cursor.fetchone()

    cursor.execute("INSERT INTO chats (usuario_id, titulo) VALUES (%s, %s)", (user['id'], titulo))
    mysql.connection.commit()
    chat_id = cursor.lastrowid  # pega o ID do novo chat

    # Redireciona diretamente para o novo chat
    return redirect(url_for('abrir_chat', chat_id=chat_id))

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    data = request.get_json()
    chat_id = data.get('chat_id')

    if not chat_id:
        return jsonify({'error': 'ID inválido'}), 400

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM mensagens WHERE chat_id = %s", (chat_id,))
    cur.execute("DELETE FROM chats WHERE id = %s", (chat_id,))
    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True})

@app.route('/edit_chat_title', methods=['POST'])
def edit_chat_title():
    data = request.get_json()
    chat_id = data.get('chat_id')
    new_title = data.get('new_title')

    if not chat_id or not new_title:
        return jsonify({'error': 'Dados inválidos'}), 400

    cur = mysql.connection.cursor()
    cur.execute("UPDATE chats SET titulo = %s WHERE id = %s", (new_title, chat_id))
    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('chat_history', None)
    session.pop('chat_id', None)
    return redirect(url_for('login'))

@app.route('/perfil')
def perfil():
    return render_template('perfil.html')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json()
    texto = data.get('message', '')
    chat_id = data.get('chat_id')
    usuario = session.get('usuario')

    if not texto or not usuario:
        return jsonify({'error': 'Dados incompletos'}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Cria chat se não houver
    if not chat_id:
        cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (usuario,))
        user = cursor.fetchone()
        cursor.execute("INSERT INTO chats (usuario_id, titulo) VALUES (%s, %s)", (user['id'], 'Nova conversa'))
        mysql.connection.commit()
        chat_id = cursor.lastrowid
        session['chat_id'] = chat_id

    resposta_openai = obter_resposta_openai(texto, chat_id)
    print(resposta_openai)

    # Atualiza título se detectar área
    area = identificar_area_juridica(resposta_openai)
    if area:
        try:
            cursor.execute("UPDATE chats SET titulo = %s WHERE id = %s", (area, chat_id))
            mysql.connection.commit()
        except Exception as e:
            print("Falha ao atualizar título:", e)

    # Se houver área, busca e grava recomendação como nova mensagem
    recomendacao_texto = None
    if area:
        recomendacao_texto = recomendar_advogado_por_area(area)
        if recomendacao_texto:
            try:
                cursor.execute(
                    "INSERT INTO mensagens (chat_id, remetente, conteudo) VALUES (%s, %s, %s)",
                    (chat_id, 'ia', recomendacao_texto)
                )
                mysql.connection.commit()
            except Exception as e:
                print("Falha ao salvar recomendação:", e)
                recomendacao_texto = None

    return jsonify(
        reply=resposta_openai,
        chat_id=chat_id,
        titulo=area or "Nova conversa",
        recommendation=recomendacao_texto
    )

if __name__ == '__main__':
    # Em produção, use um servidor WSGI (gunicorn/uwsgi). Este é apenas para desenvolvimento.
    app.run(debug=True, host='0.0.0.0', port=5000)
