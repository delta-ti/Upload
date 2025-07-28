from flask import Flask, request, send_from_directory, jsonify, render_template, session, redirect, url_for
from functools import wraps
import os
import urllib.parse
import requests
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = r'C:\Users\GRUPO_AIZ\Desktop\imagens'
app.secret_key = "chave-secreta-para-session"  # importante para cookies JWT

SUPABASE_API = "https://pbhulouvwqdzkattzckp.supabase.co/functions/v1/dynamic-endpoint"
SUPABASE_USUARIOS = "https://pbhulouvwqdzkattzckp.supabase.co/functions/v1/dynamic-action"
SUPABASE_EMPRESAS_USER = "https://pbhulouvwqdzkattzckp.supabase.co/functions/v1/quick-service"

# === Decorator para proteção ===
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("access_token"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def get_headers():
    token = session.get("access_token")
    return {
        "Authorization": f"Bearer {token}" if token else "",
        "Content-Type": "application/json"
    }

@app.route("/")
@login_required
def index():
    nome_usuario = session.get("user_nome", "")
    return render_template("index.html", nome_usuario=nome_usuario)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        payload = {"email": email, "senha": senha}
        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBiaHVsb3V2d3FkemthdHR6Y2twIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk4Mzk2MTcsImV4cCI6MjA2NTQxNTYxN30.2RixRM5TD-RUUdve4EbJME0-lkjSyIe-GL0steal-yA",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(
                "https://pbhulouvwqdzkattzckp.supabase.co/functions/v1/smooth-endpoint",
                json=payload,
                headers=headers
            )
            resp.raise_for_status()
            dados = resp.json()

            session["access_token"] = dados["access_token"]

            # Recuperar nome e sobrenome formatados
            user_metadata = dados.get("user", {}).get("user_metadata", {})
            nome = user_metadata.get("nome", "").strip().title()
            sobrenome = user_metadata.get("sobrenome", "").strip().title()
            nome_completo = f"{nome} {sobrenome}".strip() if nome or sobrenome else email

            session["user_nome"] = nome_completo

            return redirect(url_for("index"))
        except Exception as e:
            return f"Erro no login: {e}", 401

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/usuarios")
@login_required
def listar_usuarios():
    try:
        resp = requests.get(SUPABASE_USUARIOS, headers=get_headers())
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        print("Erro ao listar usuários:", e)
        return jsonify([]), 500

@app.route("/empresas_usuario/<user_id>")
@login_required
def empresas_usuario(user_id):
    try:
        url = f"{SUPABASE_EMPRESAS_USER}?usuario_id={user_id}"
        resp = requests.get(url, headers=get_headers())
        resp.raise_for_status()
        empresas = resp.json()
        empresas_aprovadas = [
            emp for emp in empresas
            if emp.get("status_aprovacao") in ("aprovado", "aprovada")
            and emp.get("usuario_id") == user_id
            and emp.get("empresa") is not None
            and (
                emp["empresa"].get("nome_fantasia") or
                emp["empresa"].get("razao_social")
            )
        ]
        return jsonify(empresas_aprovadas)
    except Exception as e:
        print("Erro ao buscar empresas do usuário:", e)
        return jsonify([]), 500

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    user_id = request.form.get('user_id')
    empresa_id = request.form.get('empresa_id')
    data_expiracao = request.form.get('data_expiracao')

    if not user_id:
        return "Usuário não informado", 400
    if 'arquivo' not in request.files:
        return "Nenhum arquivo enviado", 400

    arquivo = request.files['arquivo']
    if arquivo.filename == '':
        return "Nome de arquivo vazio", 400

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    caminho = os.path.join(app.config['UPLOAD_FOLDER'], arquivo.filename)

    if os.path.exists(caminho):
        base, ext = os.path.splitext(arquivo.filename)
        i = 1
        while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], f"{base}_{i}{ext}")):
            i += 1
        filename_final = f"{base}_{i}{ext}"
        caminho = os.path.join(app.config['UPLOAD_FOLDER'], filename_final)
    else:
        filename_final = arquivo.filename

    try:
        arquivo.save(caminho)
    except Exception as e:
        print(f"Erro ao salvar arquivo: {e}")
        return f"Erro ao salvar arquivo: {e}", 500

    nome_arquivo_url = urllib.parse.quote(filename_final)
    HOST = "192.168.0.110"
    PORT = 5001
    url_completa = f'http://{HOST}:{PORT}/imagens/{nome_arquivo_url}'

    metadados = {
        "user_id": user_id,
        "empresa_id": empresa_id if empresa_id else None,
        "nome": filename_final,
        "url": url_completa,
        "tipo": arquivo.content_type,
        "tamanho": os.path.getsize(caminho),
        "criado_em": datetime.now().isoformat(),
        "data_expiracao": data_expiracao if data_expiracao else None,
        "ativo": True,
        "status": "ativo"
    }
    metadados = {k: v for k, v in metadados.items() if v is not None}

    resp = requests.post(SUPABASE_API, headers=get_headers(), json=metadados)
    print("Resposta POST arquivos:", resp.status_code, resp.text)
    if resp.status_code in (200, 201):
        return jsonify({"url": url_completa, "msg": "Arquivo salvo e metadados enviados!"})
    else:
        return jsonify({"erro": "Erro ao salvar metadados no Supabase", "detalhe": resp.text}), 500

@app.route('/imagens/<path:nome>')
def imagens(nome):
    return send_from_directory(app.config['UPLOAD_FOLDER'], nome)

@app.route('/arquivos')
@login_required
def listar_arquivos():
    user_id = request.args.get('user_id')
    empresa_id = request.args.get('empresa_id')
    params = []
    if user_id:
        params.append(f"user_id={user_id}")
    if empresa_id:
        # Ajuste: se empresa_id for SEM_VINCULO, envie so_sem_empresa=true
        if empresa_id == "SEM_VINCULO":
            params.append("so_sem_empresa=true")
        else:
            params.append(f"empresa_id={empresa_id}")
    params.append("only_active=true")
    query = "&".join(params)
    resp = requests.get(f"{SUPABASE_API}?{query}", headers=get_headers())
    return resp.json(), resp.status_code

@app.route('/arquivo/<arquivo_id>', methods=['PATCH'])
@login_required
def deletar_arquivo(arquivo_id):
    payload = {
        "ativo": False,
        "status": "inativo"
    }
    url = f"{SUPABASE_API}?id={arquivo_id}"
    resp = requests.patch(url, headers=get_headers(), json=payload)
    print("PATCH arquivos:", resp.status_code, resp.text)
    try:
        resp_json = resp.json()
    except Exception:
        resp_json = {}

    if resp.status_code in [200, 204] or (isinstance(resp_json, dict) and resp_json.get('status') == 'ok'):
        return jsonify({"msg": "Arquivo marcado como inativo no Supabase"})
    else:
        return jsonify({"erro": "Falha ao atualizar status no Supabase", "detalhe": resp.text}), 500

if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print(">>> UPLOAD_FOLDER:", app.config['UPLOAD_FOLDER'])
    app.run(debug=True, host='0.0.0.0', port=5001)
