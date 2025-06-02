import os

TEMPLATES_DIR = "templates"
CSS_LINK = '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'style.css\') }}">\n'

for fname in os.listdir(TEMPLATES_DIR):
    if fname.endswith(".html"):
        path = os.path.join(TEMPLATES_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Verifica se já tem o link do style.css
        already_there = any("style.css" in line for line in lines)
        if already_there:
            print(f"{fname}: já possui o link do CSS.")
            continue
        
        # Procura a posição para inserir (logo após Bootstrap, se existir)
        insert_idx = -1
        for i, line in enumerate(lines):
            if "bootstrap.min.css" in line:
                insert_idx = i + 1
                break
        if insert_idx == -1:
            for i, line in enumerate(lines):
                if "<head" in line.lower():
                    insert_idx = i + 1
                    break
        
        if insert_idx == -1:
            print(f"{fname}: não encontrei <head>, pulei!")
            continue
        
        lines.insert(insert_idx, CSS_LINK)
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"{fname}: CSS link adicionado!")
