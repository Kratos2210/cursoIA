"""
app.py · Atajo de compatibilidad
=================================
El proyecto final vivía en este único archivo. Ahora está repartido en
módulos (config, rag, audit, tools, state, persistence, graph_builder, main)
para poder testearlo sin gastar cuota y cambiar de base de datos sin tocar
la lógica. Lee main.py: ahí está el mapa completo.

Este archivo se queda para que el comando de siempre siga funcionando:

    uv run python curso_ejemplos/proyecto_final/app.py

Es exactamente lo mismo que:

    uv run python curso_ejemplos/proyecto_final/main.py
"""

# Al ejecutar un script, Python pone su carpeta al principio de sys.path.
# Por eso 'import main' encuentra el main.py de esta misma carpeta.
from main import main
import config

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if config.es_error_cuota(error):
            print(config.mensaje_cuota())
        else:
            print(f"❌ Error inesperado: {error}")
