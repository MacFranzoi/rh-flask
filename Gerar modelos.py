import os
import pandas as pd

base_dir = os.path.dirname(os.path.abspath(__file__))
modelos_dir = os.path.join(base_dir, "modelos")
os.makedirs(modelos_dir, exist_ok=True)

# 1. Colaboradores
df = pd.DataFrame(columns=[
    "id", "nome", "cargo", "salario", "admissao", "departamento", "email", "telefone"
])
df.to_excel(os.path.join(modelos_dir, "modelo_colaboradores.xlsx"), index=False)
print("Modelo de colaboradores criado.")

# 2. Pontos
df = pd.DataFrame(columns=[
    "id_colaborador", "data", "entrada", "saida", "tipo_saida", "duracao_saida",
    "amamentacao_horas", "horas_extra", "horas_faltas", "observacao",
    "feriado", "horas_trabalhadas"
])
df.to_excel(os.path.join(modelos_dir, "modelo_pontos.xlsx"), index=False)
print("Modelo de pontos criado.")

# 3. Atestados
df = pd.DataFrame(columns=[
    "id_colaborador", "tipo_atestado", "data_inicio", "data_fim",
    "horas", "motivo", "arquivo"
])
df.to_excel(os.path.join(modelos_dir, "modelo_atestados.xlsx"), index=False)
print("Modelo de atestados criado.")

# 4. Feriados
df = pd.DataFrame(columns=["data", "descricao", "tipo"])
df.to_excel(os.path.join(modelos_dir, "modelo_feriados.xlsx"), index=False)
print("Modelo de feriados criado.")
