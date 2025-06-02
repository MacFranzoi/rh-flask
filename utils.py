def get_nome_colaborador(id_colaborador, colaboradores):
    for c in colaboradores:
        if str(c['id']) == str(id_colaborador):
            return c['nome']
    return id_colaborador

def calcular_horas_trabalhadas(entrada, saida, amamentacao_horas, tipo_saida, duracao_saida, jornada_padrao=8):
    from datetime import datetime
    try:
        h_entrada = datetime.strptime(entrada, "%H:%M")
        h_saida = datetime.strptime(saida, "%H:%M")
        worked = (h_saida - h_entrada).seconds / 3600
        if tipo_saida == "Almoço":
            worked -= duracao_saida
        elif tipo_saida == "Amamentação":
            pass
        elif tipo_saida in ["Consulta médica", "Assunto particular", "Outro"]:
            worked -= duracao_saida
        if amamentacao_horas:
            worked += amamentacao_horas
        worked = max(0, worked)
        return worked
    except Exception:
        return 0


# Calcula o custo total de um salário bruto considerando FGTS e INSS (empregado e patronal)
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
