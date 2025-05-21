import os
import time
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
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'DireitosConnect.mysql.pythonanywhere-services.com')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'DireitosConnect')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'IFSP2025')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'DireitosConnect$default')

mysql = MySQL(app)

def gerar_csv_advogados():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT especialidade, nome, telefone, horario_trabalho FROM advogados")
        dados = cursor.fetchall()
        linhas = ["Especialidade,Nome,Telefone,Horário de Trabalho"]
        for row in dados:
            linhas.append(f"{row['especialidade']},{row['nome']},{row['telefone']},{row['horario_trabalho']}")
        return "\n".join(linhas)
    except Exception as e:
        print("Erro ao gerar CSV:", e)
        return ""

def obter_resposta_openai(texto, chat_id=None):
    try:
        if 'chat_history' not in session:
            session['chat_history'] = []
            
            csv_advogados = gerar_csv_advogados()
            prompt = f"""
            Você é uma assistente chamada Lia, especializada em assuntos jurídicos. Seu papel é ajudar os clientes a compreenderem,
            de forma objetiva e acessível, dúvidas relacionadas a situações jurídicas que tenham enfrentado recentemente.

            Sempre que possível, identifique claramente qual é a área do direito relacionada ao problema apresentado
            (como direito civil, penal, trabalhista, tributário, entre outros) e informe essa área de forma explícita na resposta.
            Caso não seja possível definir com segurança a área jurídica, solicite mais detalhes ao cliente antes de tentar indicar.

            Apresente-se no início da sua primeira resposta. Use linguagem simples; construa suas respostas em uma estrutura de até 4 parágrafos; e evite utilizar termos jurídicos rebuscados.
            Quando for necessário usar algum termo técnico, explique-o de forma clara para garantir que qualquer pessoa, mesmo sem formação jurídica, possa entender.

            Evite suposições ou invenções. Baseie suas respostas apenas nas informações fornecidas pelo usuário e no seu conhecimento geral.
            Se faltar informação, peça mais detalhes em vez de presumir ou imaginar contextos.

            Seu tom deve ser acessível e empático, mas sempre profissional. Não ofereça conclusões legais definitivas — seu papel é orientar e esclarecer,
            não substituir a análise de um advogado.

            Quando for possível identificar a área de atuação do problema, adicionalmente você deve recomendar um advogado com a
            especialidade relacionada caso exista, montando um "cartão de visitas" com as informações do seguinte CSV:

            {csv_advogados}
            """

            if chat_id:
                # Carrega histórico de mensagens do banco
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute(
                    "SELECT remetente, conteudo FROM mensagens WHERE chat_id = %s ORDER BY enviada_em",
                    (chat_id,)
                )
                mensagens = cursor.fetchall()

                for m in mensagens:
                    session['chat_history'].append({
                        "role": "user" if m['remetente'].strip().lower() == "usuario" else "assistant",
                        "content": m['conteudo']
                    })

                session['chat_history'].insert(0, {"role": "system", "content": prompt})

            else:
                session['chat_history'].insert(0, {"role": "system", "content": prompt})

        session['chat_history'].append({"role": "user", "content": texto})

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=session['chat_history']
        )

        resposta = completion.choices[0].message.content
        session['chat_history'].append({"role": "assistant", "content": resposta})

        if chat_id:
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO mensagens (chat_id, remetente, conteudo) VALUES (%s, %s, %s)",
                           (chat_id, 'usuario', texto))
            cursor.execute("INSERT INTO mensagens (chat_id, remetente, conteudo) VALUES (%s, %s, %s)",
                           (chat_id, 'ia', resposta))
            mysql.connection.commit()

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

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (session['usuario'],))
    user = cursor.fetchone()

    cursor.execute("SELECT id, titulo FROM chats WHERE usuario_id = %s ORDER BY criado_em DESC", (user['id'],))
    chats = cursor.fetchall()

    return render_template('chat.html', chats=chats, mensagens=[])

@app.route('/chat/<int:chat_id>')
def abrir_chat(chat_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    session.pop('chat_history', None)
    session['chat_id'] = chat_id

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT remetente, conteudo FROM mensagens WHERE chat_id = %s ORDER BY enviada_em", (chat_id,))
    mensagens = cursor.fetchall()

    cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (session['usuario'],))
    user = cursor.fetchone()
    cursor.execute("SELECT id, titulo FROM chats WHERE usuario_id = %s ORDER BY criado_em DESC", (user['id'],))
    chats = cursor.fetchall()

    return render_template('chat.html', mensagens=mensagens, chats=chats)

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

    return redirect(url_for('chat'))

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
    chat_id = session.get('chat_id', None)

    resposta_openai = obter_resposta_openai(texto, chat_id)
    return jsonify(reply=resposta_openai)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
