#!/bin/bash
# Script para subir mudanças para o GitHub rapidamente

echo "Salvando e enviando alterações para o GitHub..."

# Adiciona todas as alterações
git add .

# Comenta automaticamente ou aceita comentário via argumento
if [ "$1" ]; then
  git commit -m "$1"
else
  git commit -m "Atualização rápida"
fi

git push

echo "✔️  Projeto enviado para o GitHub com sucesso!"
echo "Agora entre no PythonAnywhere e rode:"
echo "cd ~/rh-flask && git pull"
echo "E depois clique em Reload no painel web."