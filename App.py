import os
import pandas as pd
import json
import tempfile
from flask import Flask, render_template, request, redirect, send_file, flash, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from datetime import datetime
from utils import get_nome_colaborador, calcular_horas_trabalhadas

app = Flask(__name__)
app.secret_key = "supersecret"

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLAB_FILE = os.path.join(BASE_DIR, "colaboradores.json")
PONTO_FILE = os.path.join(BASE_DIR, "pontos.json")
ATESTADO_FILE = os.path.join(BASE_DIR, "atestados.json")
FERIADO_FILE = os.path.join(BASE_DIR, "feriados.json")
USER_FILE = os.path.join(BASE_DIR, "users.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MODELOS_DIR = os.path.join(BASE_DIR, "modelos")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Login model ---
class User(UserMixin):
    def __init__(self, id, email, password_hash):
        self.id = id
        self.email = email
        self.password_hash = password_hash

def load_users():
    if not os.path.exists(USER_FILE):
        return []
    with open(USER_FILE, encoding='utf-8') as f:
        return json.load(f)

def get_user_by_email(email):
    for u in load_users():
        if u["email"] == email:
            return User(u["id"], u["email"], u["password_hash"])
    return None

@login_manager.user_loader
def load_user(user_id):
    for u in load_users():
        if str(u["id"]) == str(user_id):
            return User(u["id"], u["email"], u["password_hash"])
    return None

# --- Cadastro inicial ---
@app.route("/criar_admin")
def criar_admin():
    if not os.path.exists(USER_FILE):
        email = "admin@empresa.com"
        senha = "admin123"
        password_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
        users = [{"id": 1, "email": email, "password_hash": password_hash}]
        with open(USER_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f)
        return f"Usuário admin criado! Email: {email}, Senha: {senha}"
    else:
        return "Já existe usuário admin. Delete users.json para resetar."

# --- Login / Logout ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = get_user_by_email(request.form["email"])
        if user and bcrypt.check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Usuário ou senha inválidos.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# --- Protege todas as rotas exceto login, criar_admin, static ---
@app.before_request
def protege_rotas():
    open_routes = ("login", "criar_admin", "static")
    if not current_user.is_authenticated and (request.endpoint not in open_routes):
        if not (request.endpoint or "").startswith("static"):
            return redirect(url_for("login"))

# --- Usuários ---
@app.route('/usuarios')
@login_required
def usuarios():
    users = load_users()
    return render_template('usuarios.html', usuarios=users)

@app.route('/usuarios/add', methods=['POST'])
@login_required
def add_usuario():
    if not hasattr(current_user, 'tipo') or getattr(current_user, 'tipo', None) != "admin":
        flash("Só admin pode cadastrar usuário!", "danger")
        return redirect(url_for("usuarios"))
    users = load_users()
    novo = {
        "id": max([u.get('id', 0) for u in users]+[0]) + 1,
        "nome": request.form.get('nome', ''),
        "email": request.form.get('email', ''),
        "password_hash": bcrypt.generate_password_hash(request.form.get('senha', '')).decode('utf-8'),
        "tipo": request.form.get('tipo', 'rh')
    }
    users.append(novo)
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)
    flash("Usuário cadastrado!", "success")
    return redirect(url_for("usuarios"))

@app.route('/usuarios/delete/<int:id>')
@login_required
def delete_usuario(id):
    if not hasattr(current_user, 'tipo') or getattr(current_user, 'tipo', None) != "admin":
        flash("Só admin pode excluir usuário!", "danger")
        return redirect(url_for("usuarios"))
    users = load_users()
    users = [u for u in users if u['id'] != id]
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)
    flash("Usuário excluído!", "success")
    return redirect(url_for("usuarios"))

# --- Utilidades de dados ---
def load_json(path):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- Dashboard ---
@app.route('/')
@login_required
def index():
    colabs = load_json(COLAB_FILE)
    pontos = load_json(PONTO_FILE)
    atestados = load_json(ATESTADO_FILE)
    feriados = load_json(FERIADO_FILE)
    return render_template("dashboard.html",
                           n_colabs=len(colabs),
                           n_pontos=len(pontos),
                           n_atestados=len(atestados),
                           n_feriados=len(feriados),
                           ultimos_pontos=pontos[-5:][::-1],
                           ultimos_atestados=atestados[-5:][::-1]
                           )

# --- Colaboradores ---
@app.route('/colaboradores')
@login_required
def colaboradores():
    cols = load_json(COLAB_FILE)
    return render_template("colaboradores.html", colaboradores=cols)

@app.route('/colaboradores/add', methods=['POST'])
@login_required
def add_colaborador():
    cols = load_json(COLAB_FILE)
    novo = {
        "id": request.form.get('id', '').strip(),
        "nome": request.form.get('nome', '').strip(),
        "cargo": request.form.get('cargo', '').strip(),
        "salario": request.form.get('salario', ''),
        "admissao": request.form.get('admissao', ''),
        "departamento": request.form.get('departamento', ''),
        "email": request.form.get('email', ''),
        "telefone": request.form.get('telefone', '')
    }
    cols.append(novo)
    save_json(COLAB_FILE, cols)
    flash("Colaborador adicionado!", "success")
    return redirect(url_for("colaboradores"))

@app.route('/colaboradores/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_colaborador(id):
    cols = load_json(COLAB_FILE)
    colaborador = next((c for c in cols if str(c['id']) == str(id)), None)
    if not colaborador:
        flash("Colaborador não encontrado!", "danger")
        return redirect(url_for("colaboradores"))
    if request.method == 'POST':
        colaborador['nome'] = request.form.get('nome', '').strip()
        colaborador['cargo'] = request.form.get('cargo', '').strip()
        colaborador['salario'] = request.form.get('salario', '')
        colaborador['admissao'] = request.form.get('admissao', '')
        colaborador['departamento'] = request.form.get('departamento', '')
        colaborador['email'] = request.form.get('email', '')
        colaborador['telefone'] = request.form.get('telefone', '')
        save_json(COLAB_FILE, cols)
        flash('Colaborador atualizado com sucesso!', 'success')
        return redirect(url_for('colaboradores'))
    return render_template('colaborador_edit.html', colaborador=colaborador)

@app.route('/colaboradores/delete/<id>')
@login_required
def delete_colaborador(id):
    cols = load_json(COLAB_FILE)
    cols = [c for c in cols if str(c['id']) != str(id)]
    save_json(COLAB_FILE, cols)
    flash("Colaborador excluído!", "success")
    return redirect(url_for("colaboradores"))


@app.route('/cargos')
@login_required
def cargos():
    cargos_path = os.path.join(BASE_DIR, "cargos.json")
    if not os.path.exists(cargos_path):
        with open(cargos_path, "w", encoding="utf-8") as f:
            json.dump([], f)
    with open(cargos_path, encoding="utf-8") as f:
        cargos = json.load(f)
    return render_template("cargos.html", cargos=cargos)

# --- Adiciona novo cargo ---
@app.route('/cargos/add', methods=['POST'])
@login_required
def add_cargo():
    cargos_path = os.path.join(BASE_DIR, "cargos.json")
    if not os.path.exists(cargos_path):
        cargos = []
    else:
        with open(cargos_path, encoding="utf-8") as f:
            cargos = json.load(f)
    novo = {
        "id": max([c.get('id', 0) for c in cargos] + [0]) + 1,
        "nome": request.form.get('nome', ''),
        "grupo": request.form.get('grupo', ''),
        "salario_base": float(request.form.get('salario_base', 0) or 0)
    }
    cargos.append(novo)
    with open(cargos_path, 'w', encoding='utf-8') as f:
        json.dump(cargos, f, ensure_ascii=False, indent=4)
    flash("Cargo cadastrado!", "success")
    return redirect(url_for("cargos"))

# --- Pontos ---
@app.route('/pontos')
@login_required
def pontos():
    pontos = load_json(PONTO_FILE)
    colaboradores = load_json(COLAB_FILE)
    feriados = load_json(FERIADO_FILE)
    return render_template("pontos.html", pontos=pontos, colaboradores=colaboradores, feriados=feriados)

@app.route('/pontos/add', methods=['POST'])
@login_required
def add_ponto():
    pts = load_json(PONTO_FILE)
    entrada = request.form.get('entrada', '')
    saida = request.form.get('saida', '')
    tipo_saida = request.form.get('tipo_saida', '')
    duracao_saida = float(request.form.get('duracao_saida', 0)) if request.form.get('duracao_saida') else 0
    amamentacao_horas = float(request.form.get('amamentacao_horas', 0)) if request.form.get('amamentacao_horas') else 0
    data = request.form.get('data', '')
    horas_trabalhadas = calcular_horas_trabalhadas(entrada, saida, amamentacao_horas, tipo_saida, duracao_saida)
    novo = {
        "id_colaborador": request.form.get('id_colaborador', ''),
        "data": data,
        "entrada": entrada,
        "saida": saida,
        "tipo_saida": tipo_saida,
        "duracao_saida": duracao_saida,
        "amamentacao_horas": amamentacao_horas,
        "horas_extra": float(request.form.get('horas_extra', 0)) if request.form.get('horas_extra') else 0,
        "horas_faltas": float(request.form.get('horas_faltas', 0)) if request.form.get('horas_faltas') else 0,
        "observacao": request.form.get('observacao', ''),
        "feriado": request.form.get('feriado', ''),
        "horas_trabalhadas": horas_trabalhadas
    }
    pts.append(novo)
    save_json(PONTO_FILE, pts)
    flash("Ponto registrado!", "success")
    return redirect(url_for("pontos"))

@app.route('/pontos/edit/<int:idx>', methods=['GET', 'POST'])
@login_required
def edit_ponto(idx):
    pts = load_json(PONTO_FILE)
    if idx < 0 or idx >= len(pts):
        flash("Registro de ponto não encontrado!", "danger")
        return redirect(url_for("pontos"))
    ponto = pts[idx]
    colaboradores = load_json(COLAB_FILE)
    feriados = load_json(FERIADO_FILE)
    if request.method == 'POST':
        ponto['id_colaborador'] = request.form.get('id_colaborador', '')
        ponto['data'] = request.form.get('data', '')
        ponto['entrada'] = request.form.get('entrada', '')
        ponto['saida'] = request.form.get('saida', '')
        ponto['tipo_saida'] = request.form.get('tipo_saida', '')
        ponto['duracao_saida'] = float(request.form.get('duracao_saida', 0)) if request.form.get('duracao_saida') else 0
        ponto['amamentacao_horas'] = float(request.form.get('amamentacao_horas', 0)) if request.form.get('amamentacao_horas') else 0
        ponto['horas_extra'] = float(request.form.get('horas_extra', 0)) if request.form.get('horas_extra') else 0
        ponto['horas_faltas'] = float(request.form.get('horas_faltas', 0)) if request.form.get('horas_faltas') else 0
        ponto['observacao'] = request.form.get('observacao', '')
        ponto['feriado'] = request.form.get('feriado', '')
        ponto['horas_trabalhadas'] = calcular_horas_trabalhadas(
            ponto['entrada'], ponto['saida'], ponto['amamentacao_horas'], ponto['tipo_saida'], ponto['duracao_saida']
        )
        save_json(PONTO_FILE, pts)
        flash("Registro de ponto atualizado!", "success")
        return redirect(url_for("pontos"))
    return render_template("ponto_edit.html", ponto=ponto, idx=idx, colaboradores=colaboradores, feriados=feriados)

@app.route('/pontos/delete/<int:idx>')
@login_required
def delete_ponto(idx):
    pts = load_json(PONTO_FILE)
    if 0 <= idx < len(pts):
        pts.pop(idx)
        save_json(PONTO_FILE, pts)
        flash("Registro de ponto excluído!", "success")
    return redirect(url_for("pontos"))

# --- Atestados ---
@app.route('/atestados')
@login_required
def atestados():
    atestados = load_json(ATESTADO_FILE)
    colaboradores = load_json(COLAB_FILE)
    return render_template("atestados.html", atestados=atestados, colaboradores=colaboradores)

@app.route('/atestados/add', methods=['POST'])
@login_required
def add_atestado():
    atestados = load_json(ATESTADO_FILE)
    colaborador_id = request.form.get('id_colaborador', '')
    tipo_atestado = request.form.get('tipo_atestado', '')
    motivo = request.form.get('motivo', '')
    arquivo = request.files.get('arquivo')
    filename = ""
    if arquivo and arquivo.filename:
        filename = secure_filename(f"{colaborador_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{arquivo.filename}")
        arquivo.save(os.path.join(UPLOAD_DIR, filename))
    if tipo_atestado == 'dias':
        data_inicio = request.form.get('data_inicio', '')
        data_fim = request.form.get('data_fim', '')
        horas = ""
    else:
        data_inicio = request.form.get('data_hora', '')
        data_fim = request.form.get('data_hora', '')
        horas = request.form.get('horas', '')
    novo = {
        "id_colaborador": colaborador_id,
        "tipo_atestado": tipo_atestado,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "horas": horas,
        "motivo": motivo,
        "arquivo": filename
    }
    atestados.append(novo)
    save_json(ATESTADO_FILE, atestados)
    flash("Atestado registrado!", "success")
    return redirect(url_for("atestados"))

@app.route('/atestados/edit/<int:idx>', methods=['GET', 'POST'])
@login_required
def edit_atestado(idx):
    atestados = load_json(ATESTADO_FILE)
    if idx < 0 or idx >= len(atestados):
        flash("Atestado não encontrado!", "danger")
        return redirect(url_for("atestados"))
    a = atestados[idx]
    colaboradores = load_json(COLAB_FILE)
    if request.method == 'POST':
        a['id_colaborador'] = request.form.get('id_colaborador', '')
        a['tipo_atestado'] = request.form.get('tipo_atestado', '')
        if a['tipo_atestado'] == 'dias':
            a['data_inicio'] = request.form.get('data_inicio', '')
            a['data_fim'] = request.form.get('data_fim', '')
            a['horas'] = ""
        else:
            a['data_inicio'] = request.form.get('data_hora', '')
            a['data_fim'] = request.form.get('data_hora', '')
            a['horas'] = request.form.get('horas', '')
        a['motivo'] = request.form.get('motivo', '')
        arquivo = request.files.get('arquivo')
        if arquivo and arquivo.filename:
            filename = secure_filename(f"{a['id_colaborador']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{arquivo.filename}")
            arquivo.save(os.path.join(UPLOAD_DIR, filename))
            a['arquivo'] = filename
        save_json(ATESTADO_FILE, atestados)
        flash("Atestado atualizado!", "success")
        return redirect(url_for("atestados"))
    return render_template("atestado_edit.html", atestado=a, idx=idx, colaboradores=colaboradores)

@app.route('/atestados/delete/<int:idx>')
@login_required
def delete_atestado(idx):
    atestados = load_json(ATESTADO_FILE)
    if 0 <= idx < len(atestados):
        atestados.pop(idx)
        save_json(ATESTADO_FILE, atestados)
        flash("Atestado excluído!", "success")
    return redirect(url_for("atestados"))

@app.route('/atestados/download/<filename>')
@login_required
def download_atestado_file(filename):
    return send_file(os.path.join(UPLOAD_DIR, filename), as_attachment=True)

# --- Feriados ---
@app.route('/feriados')
@login_required
def feriados():
    feriados = load_json(FERIADO_FILE)
    return render_template("feriados.html", feriados=feriados)

@app.route('/feriados/add', methods=['POST'])
@login_required
def add_feriado():
    feriados = load_json(FERIADO_FILE)
    novo = {
        "data": request.form.get('data', ''),
        "descricao": request.form.get('descricao', ''),
        "tipo": request.form.get('tipo', '')
    }
    feriados.append(novo)
    save_json(FERIADO_FILE, feriados)
    flash("Feriado cadastrado!", "success")
    return redirect(url_for("feriados"))

@app.route('/feriados/edit/<int:idx>', methods=['GET', 'POST'])
@login_required
def edit_feriado(idx):
    feriados = load_json(FERIADO_FILE)
    if idx < 0 or idx >= len(feriados):
        flash("Feriado não encontrado!", "danger")
        return redirect(url_for("feriados"))
    f = feriados[idx]
    if request.method == 'POST':
        f['data'] = request.form.get('data', '')
        f['descricao'] = request.form.get('descricao', '')
        f['tipo'] = request.form.get('tipo', '')
        save_json(FERIADO_FILE, feriados)
        flash("Feriado atualizado!", "success")
        return redirect(url_for("feriados"))
    return render_template("feriado_edit.html", feriado=f, idx=idx)

@app.route('/feriados/delete/<int:idx>')
@login_required
def delete_feriado(idx):
    feriados = load_json(FERIADO_FILE)
    if 0 <= idx < len(feriados):
        feriados.pop(idx)
        save_json(FERIADO_FILE, feriados)
        flash("Feriado excluído!", "success")
    return redirect(url_for("feriados"))

# --- Importação/Exportação/Modelo Excel ---
@app.route('/export/<tipo>')
@login_required
def export(tipo):
    if tipo == "colaboradores":
        data = load_json(COLAB_FILE)
        df = pd.DataFrame(data)
        filename = "colaboradores_export.xlsx"
    elif tipo == "pontos":
        data = load_json(PONTO_FILE)
        colaboradores = {c['id']: c['nome'] for c in load_json(COLAB_FILE)}
        for p in data:
            p['nome_colaborador'] = colaboradores.get(str(p['id_colaborador']), p['id_colaborador'])
        df = pd.DataFrame(data)
        cols = ['nome_colaborador'] + [col for col in df.columns if col != 'nome_colaborador' and col != 'id_colaborador']
        df = df[cols]
        filename = "pontos_export.xlsx"
    elif tipo == "atestados":
        data = load_json(ATESTADO_FILE)
        colaboradores = {c['id']: c['nome'] for c in load_json(COLAB_FILE)}
        for a in data:
            a['nome_colaborador'] = colaboradores.get(str(a['id_colaborador']), a['id_colaborador'])
        df = pd.DataFrame(data)
        cols = ['nome_colaborador'] + [col for col in df.columns if col != 'nome_colaborador' and col != 'id_colaborador']
        df = df[cols]
        filename = "atestados_export.xlsx"
    elif tipo == "feriados":
        data = load_json(FERIADO_FILE)
        df = pd.DataFrame(data)
        filename = "feriados_export.xlsx"
    else:
        return "Tipo não reconhecido", 400

    tmp_dir = tempfile.gettempdir()
    tmp_file = os.path.join(tmp_dir, filename)
    df.to_excel(tmp_file, index=False)
    return send_file(tmp_file, as_attachment=True)

@app.route('/modelo/<tipo>')
@login_required
def modelo(tipo):
    filename = os.path.join(MODELOS_DIR, f"modelo_{tipo}.xlsx")
    return send_file(os.path.abspath(filename), as_attachment=True)

@app.route('/import/<tipo>', methods=['POST'])
@login_required
def importar(tipo):
    file = request.files['file']
    if file.filename == '':
        flash("Nenhum arquivo selecionado", "danger")
        return redirect(request.referrer)
    df = pd.read_excel(file)
    data = df.to_dict(orient='records')
    if tipo == "colaboradores":
        save_json(COLAB_FILE, data)
        flash("Colaboradores importados!", "success")
    elif tipo == "pontos":
        save_json(PONTO_FILE, data)
        flash("Pontos importados!", "success")
    elif tipo == "atestados":
        save_json(ATESTADO_FILE, data)
        flash("Atestados importados!", "success")
    elif tipo == "feriados":
        save_json(FERIADO_FILE, data)
        flash("Feriados importados!", "success")
    return redirect(url_for(tipo))


# --- Folha de Pagamento ---
import collections

def calcular_custo_total(salario_bruto):
    fgts = salario_bruto * 0.08
    # INSS empregado (simplificado)
    if salario_bruto <= 1412:
        inss = salario_bruto * 0.075
    elif salario_bruto <= 2666.68:
        inss = salario_bruto * 0.09
    elif salario_bruto <= 4000.03:
        inss = salario_bruto * 0.12
    else:
        inss = salario_bruto * 0.14
    inss_patronal = salario_bruto * 0.2
    custo_total = salario_bruto + fgts + inss_patronal
    return {
        "salario": salario_bruto,
        "fgts": fgts,
        "inss_empregado": inss,
        "inss_patronal": inss_patronal,
        "custo_total": custo_total
    }

@app.route('/folha')
@login_required
def folha_pagamento():
    colaboradores = load_json(COLAB_FILE)
    try:
        with open('cargos.json', encoding='utf-8') as f:
            cargos = json.load(f)
    except Exception:
        cargos = []
    dados_folha = []
    for c in colaboradores:
        cargo = next((cg for cg in cargos if cg['nome'] == c.get('cargo')), None)
        salario_base = cargo['salario_base'] if cargo else float(c.get('salario', 0) or 0)
        custos = calcular_custo_total(salario_base)
        dados_folha.append({
            "nome": c['nome'],
            "cargo": c.get('cargo', ''),
            "grupo": cargo['grupo'] if cargo else "",
            **custos
        })
    return render_template('folha_pagamento.html', dados=dados_folha)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
