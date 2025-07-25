from flask import Flask, request, send_from_directory, jsonify, render_template
import os
import urllib.parse
import requests
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = r'C:\Users\GRUPO_AIZ\Desktop\imagens'

SUPABASE_API = "https://pbhulouvwqdzkattzckp.supabase.co/functions/v1/dynamic-endpoint"
SUPABASE_USUARIOS = "https://pbhulouvwqdzkattzckp.supabase.co/functions/v1/dynamic-action"
SUPABASE_EMPRESAS_USER = "https://pbhulouvwqdzkattzckp.supabase.co/functions/v1/quick-service"
SUPABASE_API_TOKEN = "SEU_TOKEN_DO_SERVICE_ROLE"  # Substitua pelo seu token

API_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6IlhnT29Wcyt6MmJ0cjBnL3IiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3BiaHVsb3V2d3FkemthdHR6Y2twLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiZGVjY2NkMC02MjMwLTQyYjQtOTEyNi0wOTU1NjZkZjc3NTgiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzUzNDY2NDU3LCJpYXQiOjE3NTM0NjI4NTcsImVtYWlsIjoiamVhbi5zaWx2YUBncnVwb2Fpei5jb20uYnIiLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJub21lIjoiSmVhbiIsIm9yaWdlbV9jYWRhc3Ryb19pZCI6IjRiZTY1ZDUyLTNkYjgtNDYzNS04MWQxLWUxMDg1ODgzYzQ4ZSIsInNvYnJlbm9tZSI6ImplYW4iLCJ0ZWxlZm9uZSI6IjE0MjE0MjE0MjE0MjE0In0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3NTM0NjI4NTd9XSwic2Vzc2lvbl9pZCI6ImQ1ZjMwYTQzLTZiNjAtNDUzZS05YzMyLWRjMDdlZDk3MjM2NCIsImlzX2Fub255bW91cyI6ZmFsc2V9.2gEitvoDEKQ_gVEZnr4gWhsGErn48uLu6IBswlvl6ZM",  # Troque aqui pelo JWT correto
    "Content-Type": "application/json"
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/usuarios")
def listar_usuarios():
    try:
        resp = requests.get(SUPABASE_USUARIOS, headers=API_HEADERS)
        resp.raise_for_status()
        usuarios = resp.json()
        return jsonify(usuarios)
    except Exception as e:
        print("Erro ao listar usuários:", e)
        return jsonify([]), 500

# NOVO: Empresas do usuário filtradas por aprovado
@app.route("/empresas_usuario/<user_id>")
def empresas_usuario(user_id):
    try:
        url = f"{SUPABASE_EMPRESAS_USER}?usuario_id={user_id}"
        resp = requests.get(url, headers=API_HEADERS)
        resp.raise_for_status()
        empresas = resp.json()
        # Apenas empresas aprovadas, vinculadas ao usuário, com dados de empresa válidos
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

    # Evita sobrescrever arquivos
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
    HOST = "192.168.0.99"
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

    resp = requests.post(
        SUPABASE_API,
        headers=API_HEADERS,
        json=metadados
    )
    print("Resposta POST arquivos:", resp.status_code, resp.text)
    if resp.status_code in (200, 201):
        return jsonify({"url": url_completa, "msg": "Arquivo salvo e metadados enviados!"})
    else:
        return jsonify({"erro": "Erro ao salvar metadados no Supabase", "detalhe": resp.text}), 500

@app.route('/imagens/<path:nome>')
def imagens(nome):
    return send_from_directory(app.config['UPLOAD_FOLDER'], nome)

@app.route('/arquivos')
def listar_arquivos():
    user_id = request.args.get('user_id')
    empresa_id = request.args.get('empresa_id')
    params = []
    if user_id:
        params.append(f"user_id={user_id}")
    if empresa_id:
        params.append(f"empresa_id={empresa_id}")
    params.append("only_active=true")
    query = "&".join(params)
    resp = requests.get(
        f"{SUPABASE_API}?{query}",
        headers=API_HEADERS
    )
    return resp.json(), resp.status_code

@app.route('/arquivo/<arquivo_id>', methods=['PATCH'])
def deletar_arquivo(arquivo_id):
    payload = {
        "ativo": False,
        "status": "inativo"
    }
    url = f"{SUPABASE_API}?id={arquivo_id}"  # PATCH padrão para Edge Function (sem eq.)
    resp = requests.patch(url, headers=API_HEADERS, json=payload)
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
