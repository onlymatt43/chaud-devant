#!/bin/bash
cd "$(dirname "$0")"
echo "👀 Lancement du moniteur de dossiers (Auto Watch)..."
echo "📂 Dossiers surveillés :"
echo "   - exports_from_davinci/new (Public)"
echo "   - exports_from_davinci/private (Privé)"
echo "---------------------------------------------------"

# Utiliser le même Python que les autres scripts
export PATH="/opt/homebrew/bin:$PATH"
PYTHON_EXEC="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"

if [ ! -f "$PYTHON_EXEC" ]; then
    echo "⚠️  Python spécifique non trouvé, utilisation de 'python3' par défaut."
    PYTHON_EXEC="python3"
fi

"$PYTHON_EXEC" auto_watch.py

echo " "
echo "❌ Le script s'est arrêté."
read -p "Appuie sur Entrée pour fermer..."
