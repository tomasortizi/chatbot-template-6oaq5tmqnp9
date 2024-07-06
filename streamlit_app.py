import streamlit as st
import pandas as pd
from openai import OpenAI
from openai.error import OpenAIError

# URL del archivo CSV en GitHub
csv_url = 'https://raw.githubusercontent.com/usuario/repositorio/rama/archivo.csv'

# Mostrar título y descripción.
st.title("💬 Chatbot de Inversiones Inmobiliarias en Santiago")
st.write(
    "Este es un chatbot que recomienda los mejores departamentos para invertir en Santiago basado en tu capacidad de pago y las tasas hipotecarias actuales."
)

# Preguntar al usuario por el pie y el dividendo esperado.
pie_uf = st.number_input("¿Cuánto pie puedes pagar en UF?", min_value=0.0, step=0.1)
dividendo_clp = st.number_input("¿Cuánto dividendo esperas pagar mensualmente en CLP?", min_value=0.0, step=10000.0)

# Cargar la base de datos de departamentos desde el archivo CSV en GitHub.
@st.cache
def load_data(url):
    return pd.read_csv(url)

departamentos = load_data(csv_url)

# Simulación de tasa de crédito hipotecario (normalmente se obtendría de `www.siii.cl`).
tasa_credito = 0.04  # 4% anual

def calcular_dividendo(precio, pie, tasa, años=25):
    monto_credito = precio - pie
    tasa_mensual = tasa / 12
    meses = años * 12
    dividendo = (monto_credito * tasa_mensual) / (1 - (1 + tasa_mensual) ** -meses)
    return dividendo

# Botón para iniciar la búsqueda de departamentos
if st.button("Buscar Departamentos"):
    if not pie_uf or not dividendo_clp:
        st.error("Por favor, ingresa tanto el pie como el dividendo esperado.")
    else:
        # Asumiendo un arriendo promedio mensual de departamentos similares.
        # Esta columna debería existir en el CSV; si no, se debe calcular o estimar.
        if 'Arriendo Promedio' not in departamentos.columns:
            st.error("La base de datos de departamentos no contiene la columna 'Arriendo Promedio'.")
        else:
            # Calculamos el dividendo y la rentabilidad.
            departamentos["Pie (UF)"] = pie_uf
            departamentos["Dividendo Mensual (UF)"] = departamentos["Precio"].apply(lambda x: calcular_dividendo(x, pie_uf, tasa_credito))
            departamentos["Dividendo Mensual (CLP)"] = departamentos["Dividendo Mensual (UF)"] * 30000  # Asumimos UF a CLP es 30,000.
            departamentos["Rentabilidad (%)"] = ((departamentos["Arriendo Promedio"] * 12) / (departamentos["Precio"] * 30000)) * 100

            # Filtrar por rentabilidad y que el arriendo sea mayor al dividendo.
            resultados = departamentos[(departamentos["Arriendo Promedio"] > departamentos["Dividendo Mensual (CLP)"])]

            # Mostrar resultados.
            st.write(resultados)

            # Permitir la descarga de los resultados.
            st.download_button(
                label="Descargar Resultados",
                data=resultados.to_csv(index=False).encode('utf-8'),
                file_name='resultados_departamentos.csv',
                mime='text/csv'
            )
