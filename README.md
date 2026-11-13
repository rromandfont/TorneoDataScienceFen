Predictor adaptativo USD/CLP de 11 variables
Repositorio de entrega para el torneo Data Science en Finanzas: ¿Sube o baja el dólar mañana? (FEN UChile, Banco Itaú y Bloomberg). Al cierre de cada jornada, el modelo estima si el USD/CLP subirá o bajará en la jornada siguiente y define una exposición de −1, 0 o +1 vez el nocional. El backtest descuenta carry y costos de transacción, y el repositorio entrega la señal del día, las estadísticas de trading contra las tres referencias de las bases y un informe en PDF.
Estructura del proyecto
estrategia_usdclp_11v.ipynb: notebook principal y archivo que hay que ejecutar. Contiene los supuestos, el mecanismo de ejecución, el backtest con sus estadísticas, los gráficos y la señal del día.
codigo/modelo_adaptativo.py: módulo con toda la lógica del modelo (datos, señales, pesos dinámicos, exposición y evaluación). También se puede ejecutar por línea de comandos.
codigo/comparar_estrategias.py, codigo/grafico_desempeno.py y codigo/grafico_costos.py: análisis complementarios (variantes de exposición, curva de desempeño y sensibilidad a costos).
datos/base_usdclp.xlsx: base Bloomberg del torneo, con datos hasta el 6 de noviembre de 2026.
documentacion/: bases del torneo y diccionario de datos.
informe/: informe PDF y figuras.
resultados/: salidas de cada corrida por línea de comandos. Se llena al ejecutar y no se sube al repositorio.
resultados_referencia/: salidas esperadas con la base incluida, para verificar que la ejecución es correcta.
requirements.txt: dependencias con versiones exactas.
Ejecución desde cero
1. Requisitos
Python 3.11 o superior. Las versiones de requirements.txt se probaron con Python 3.13.
2. Crear el entorno e instalar las dependencias
Desde la carpeta raíz del repositorio:
Crear el entorno: python -m venv .venv
Activarlo en Windows: .venv\Scripts\activate
Activarlo en macOS o Linux: source .venv/bin/activate
Instalar las dependencias: pip install -r requirements.txt
3. Ubicar la base de datos
La base debe estar en datos/base_usdclp.xlsx, con la hoja datos en formato ancho: una fila por fecha en la columna fecha y una columna por serie con el nombre TICKER|CAMPO. Para usar una base más reciente, basta con reemplazar ese archivo y mantener el mismo nombre y formato.
4. Ejecutar
Todos los comandos se ejecutan desde la carpeta raíz del repositorio, porque las rutas son relativas a ella.
Notebook principal, interactivo: jupyter notebook estrategia_usdclp_11v.ipynb, y luego ejecutar todas las celdas.
Notebook principal, sin abrirlo: jupyter nbconvert --to notebook --execute --inplace estrategia_usdclp_11v.ipynb
Modelo por línea de comandos: python codigo/modelo_adaptativo.py. Deja las salidas en resultados/ (métricas, diario, pesos, lectura de la convicción, curva y señal del día).
La ejecución tarda alrededor de un minuto. Es determinista: el bootstrap usa una semilla fija y la regresión logística no tiene componentes aleatorios.
5. Verificar la ejecución
Después de ejecutar python codigo/modelo_adaptativo.py con la base incluida (hasta el 6 de noviembre de 2026), los archivos de resultados/ deben ser idénticos a los de resultados_referencia/.
6. Uso diario en el monitoreo en vivo
Agregar a datos/base_usdclp.xlsx la fila de la jornada recién cerrada.
Ejecutar python codigo/modelo_adaptativo.py.
Leer la señal en resultados/senal_del_dia_torneo.json (fecha, dirección, probabilidad y exposición) y registrarla antes de conocer el resultado.
La exposición rige desde el cierre de esa jornada hasta el cierre de la siguiente.
7. Opciones de la línea de comandos
--xlsx: ruta de otra base.
--costo_bps: costo de transacción en puntos base (3 por defecto).
--modo estricto: los cierres de Nueva York y Londres entran con un día de rezago.
--todas: usa las 16 señales originales.
--salida: carpeta de salida.
