from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'protocolo_encriptado_007'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sala_hacker.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)

# MODELOS DE BASE DE DATOS
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    nombre_anonimo = db.Column(db.String(50), nullable=False)
    foto_perfil = db.Column(db.String(300), nullable=False)
    es_master = db.Column(db.Boolean, default=False)
    esta_muteado = db.Column(db.Boolean, default=False)

class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    usuario = db.relationship('Usuario', backref=db.backref('mensajes', lazy=True))

# CREACIÓN DE TU CUENTA MASTER AUTOMÁTICA
with app.app_context():
    db.create_all()
    master = Usuario.query.filter_by(correo='dairoalexandersolartechavez@gmail.com').first()
    if not master:
        master = Usuario(
            correo='dairoalexandersolartechavez@gmail.com',
            password='Dairo123@',
            nombre_anonimo='D-Xploit',
            foto_perfil='/static/descarga.jpg',
            es_master=True
        )
        db.session.add(master)
        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        password = request.form.get('password')
        nombre_custom = request.form.get('nombre_anonimo')
        
        user = Usuario.query.filter_by(correo=correo).first()
        
        if user:
            if user.password == password:
                session['user_id'] = user.id
                return redirect(url_for('chat'))
            else:
                return "ACCESO DENEGADO: Contraseña incorrecta."
        else:
            # Registrar nuevo usuario (los mortales)
            alias = nombre_custom if nombre_custom else f"Anon_{random.randint(100, 999)}"
            nuevo_user = Usuario(
                correo=correo, 
                password=password, 
                nombre_anonimo=alias, 
                foto_perfil='/static/descarga.jpg'
            )
            db.session.add(nuevo_user)
            db.session.commit()
            session['user_id'] = nuevo_user.id
            return redirect(url_for('chat'))
            
    return render_template('login.html')

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = Usuario.query.get(session['user_id'])
    return render_template('chat.html', usuario=user)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# WEBSOCKETS Y COMANDOS HACKER
@socketio.on('connect')
def handle_connect():
    user = Usuario.query.get(session['user_id'])
    historial = Mensaje.query.order_by(Mensaje.fecha.asc()).all()
    
    # Enviar historial al que se conecta
    for msg in historial:
        emit('recibir_mensaje', {
            'texto': msg.contenido,
            'usuario': msg.usuario.nombre_anonimo,
            'avatar': msg.usuario.foto_perfil,
            'es_master': msg.usuario.es_master
        })

@socketio.on('enviar_mensaje')
def handle_message(data):
    user = Usuario.query.get(session['user_id'])
    texto = data['texto'].strip()
    
    if user.esta_muteado:
        emit('sistema_msg', {'texto': 'ACCESO DENEGADO: Estás silenciado por el Master.'})
        return

    # LOGICA DE COMANDOS PARA EL MASTER (D-Xploit)
    if texto.startswith('/') and user.es_master:
        partes = texto.split(' ', 2)
        comando = partes[0]
        
        if comando == '/correos':
            todos = Usuario.query.all()
            lista = "<br>".join([f"{u.nombre_anonimo} -> {u.correo}" for u in todos])
            emit('sistema_msg', {'texto': f'BASE DE DATOS DE CORREOS:<br>{lista}'})
            return
            
        elif comando == '/mutear' and len(partes) >= 2:
            target = Usuario.query.filter_by(nombre_anonimo=partes[1]).first()
            if target:
                target.esta_muteado = True
                db.session.commit()
                emit('sistema_msg', {'texto': f'El usuario {target.nombre_anonimo} ha sido silenciado.'}, broadcast=True)
            return

        elif comando == '/expulsar' and len(partes) >= 2:
            target = Usuario.query.filter_by(nombre_anonimo=partes[1]).first()
            if target:
                emit('accion_admin', {'accion': 'kick', 'usuario': target.nombre_anonimo}, broadcast=True)
                emit('sistema_msg', {'texto': f'El usuario {target.nombre_anonimo} fue expulsado de la red.'}, broadcast=True)
            return
            
        elif comando == '/advertir' and len(partes) >= 3:
            target_name = partes[1]
            mensaje_adv = partes[2]
            emit('accion_admin', {'accion': 'warn', 'usuario': target_name, 'mensaje': mensaje_adv}, broadcast=True)
            return

    # Si es un mensaje normal, guardarlo y enviarlo
    if not texto.startswith('/'):
        nuevo_mensaje = Mensaje(contenido=texto, usuario_id=user.id)
        db.session.add(nuevo_mensaje)
        db.session.commit()
        
        emit('recibir_mensaje', {
            'texto': texto,
            'usuario': user.nombre_anonimo,
            'avatar': user.foto_perfil,
            'es_master': user.es_master
        }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)