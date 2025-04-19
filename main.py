from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import bcrypt
import openai
import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv(dotenv_path='/home/DireitosConnect/mysite/.env')

# Agora as variáveis de ambiente estão carregadas, então você pode acessá-las
organization_id = os.getenv("ORGANIZATION_ID")  # Corrigido para acessar a variável de ambiente corretamente

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.secret_key = 'Direito'

# Configuração do banco de dados
app.config['MYSQL_HOST'] = 'DireitosConnect.mysql.pythonanywhere-services.com'
app.config['MYSQL_USER'] = 'DireitosConnect'
app.config['MYSQL_PASSWORD'] = 'IFSP2025'
app.config['MYSQL_DB'] = 'DireitosConnect$default'

mysql = MySQL(app)

@app.route('/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
        user = cursor.fetchone()

        if user:
            if bcrypt.checkpw(senha.encode('utf-8'), user['senha'].encode('utf-8')):
                session['usuario'] = usuario
                return redirect(url_for('chat'))
            else:
                msg = 'Senha incorreta.'
        else:
            msg = 'Usuário não encontrado.'

    return render_template('login.html', msg=msg)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    msg = ''
    if request.method == 'POST':
        nome = request.form['nome']
        usuario = request.form['usuario']
        email = request.form['email']
        telefone = request.form['telefone']
        senha = request.form['senha']
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

@app.route('/chatBackup')
def chatchatBackup():
    return render_template('chatBackup.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/perfil')
def perfil():
    return render_template('perfil.html')

# NOVA ROTA PARA CHAMAR A OPENAI - atualizado para openai >= 1.0.0
@app.route('/chatgpt', methods=['POST'])
def chatgpt():
    mensagem = request.form.get('mensagem')

    try:
        client = openai.OpenAI(api_key=openai.api_key)  # nova forma de instanciar o cliente
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente jurídico inteligente e prestativo."},
                {"role": "user", "content": mensagem}
            ]
        )
        resposta = response.choices[0].message.content.strip()
        return jsonify({'resposta': resposta})
    except Exception as e:
        return jsonify({'erro': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
