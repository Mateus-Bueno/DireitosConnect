import os
import time

from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import bcrypt
from dotenv import load_dotenv

from openai import OpenAI  # só precisamos desta classe

# Carrega variáveis do arquivo .env
load_dotenv(dotenv_path='/home/DireitosConnect/mysite/.env')

# Instancia o client usando a chave correta do .env
client = OpenAI(api_key=os.getenv('openai_key'))

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'Direito')

# Configuração do banco de dados
app.config['MYSQL_HOST']     = os.getenv('MYSQL_HOST', 'DireitosConnect.mysql.pythonanywhere-services.com')
app.config['MYSQL_USER']     = os.getenv('MYSQL_USER', 'DireitosConnect')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'IFSP2025')
app.config['MYSQL_DB']       = os.getenv('MYSQL_DB', 'DireitosConnect$default')

mysql = MySQL(app)

def obter_resposta_openai(texto):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
                                Você é uma assistente chamada Lia, especializada em assuntos jurídicos. Seu papel é esclarecer possíveis
                                dúvidas dos clientes com relação a qualquer problema que tenham enfrentado recentemente, além de identificar
                                qual a área de especialização que mais se adeque a esse problema. Se apresente no início de sua primeira resposta
                                e, às entradas que tragam alguma dúvida jurídica nova, sempre indique explicitamente a área de especialização.
                                Caso não seja possível definir a área de atuação a partir de apenas uma interação, peça por mais detalhes.

                                Suas respostas sempre devem evitar termos rebuscados da área de direito, ou explicar claramente o significado destes
                                quando necessário, isso visando possibilitar maior acessibilidade na conversa. Tente sempre falar de forma casual, porém
                                mantendo o profissionalismo, de forma a dar maior credibilidade ao que esta sendo discutido.
                               """
                },
                {"role": "user", "content": texto}
            ]
        )
        return completion.choices[0].message.content

    except Exception as e:
        # captura qualquer erro (incluindo rate limits)
        print("Erro ao chamar OpenAI:", e)
        time.sleep(60)
        return obter_resposta_openai(texto)

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
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data  = request.get_json()
    texto = data.get('message', '')
    reply = obter_resposta_openai(texto)
    return jsonify(reply=reply)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/perfil')
def perfil():
    return render_template('perfil.html')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
