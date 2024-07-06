import streamlit as st
import pandas as pd
from openai import OpenAI

# Show title and description.
st.title("💬 Chatbot de Inversiones Inmobiliarias en Santiago")
st.write(
    "Este es un chatbot que recomienda los mejores departamentos para invertir en Santiago basado en tu capacidad de pago y las tasas hipotecarias actuales."
)

# Preguntar al usuario por el pie y el dividendo esperado.
pie_uf = st.number_input("¿Cuánto pie puedes pagar en UF?", min_value=0.0, step=0.1)
dividendo_clp = st.number_input("¿Cuánto dividendo esperas pagar mensualmente en CLP?", min_value=0.0, step=10000.0)

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
# Usar la clave API de OpenAI directamente
openai_api_key = "sk-proj-fw1qCdqAYdEuLwq6cHJRT3BlbkFJ12Hjuv4DEdunGEYT5YJJ"
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    if "messages" not in st.session_state:
        st.session_state.messages = []

     # Definir los nombres de columnas esperados
    expected_columns = ["Precio", "Metros Cuadrados", "Dormitorios", "Baños", "Link"]


    # Cargar base de datos de departamentos desde GitHub.
    @st.cache_data
    def load_data(url):
        data = pd.read_csv(url)
        return data

    url = "https://raw.githubusercontent.com/tomasortizi/chatbot-template-6oaq5tmqnp9/main/departamentos_en_venta.csv"
    departamentos = load_data(url)

    # Validar las columnas del archivo CSV
    if all(column in departamentos.columns for column in expected_columns):
        # Asegurarse de que los valores de pie_uf y dividendo_clp sean del mismo tipo que la columna Precio
        if pie_uf is not None and dividendo_clp is not None:
            try:
                pie_uf = type(departamentos["Precio"].iloc[0])(pie_uf)
                dividendo_clp = type(departamentos["Precio"].iloc[0])(dividendo_clp)
            except ValueError:
                st.error("Los valores de pie y dividendo no son compatibles con el tipo de datos de los precios en la base de datos.")
                st.stop()
        else:
            st.error("Por favor, ingresa valores válidos para el pie y el dividendo esperado.")
            st.stop()

        # Simulación de tasa de crédito hipotecario (normalmente se obtendría de `www.siii.cl`).
        tasa_credito = 0.048  # 4% anual

        def calcular_dividendo(precio, pie, tasa, años=25):
            monto_credito = precio - pie
            tasa_mensual = tasa / 12
            meses = años * 12
            dividendo = (monto_credito * tasa_mensual) / (1 - (1 + tasa_mensual) ** -meses)
            return dividendo

        # Botón para iniciar la búsqueda de departamentos
        if st.button("Buscar Departamentos"):
            if pie_uf <= 0 or dividendo_clp <= 0:
                st.error("Por favor, ingresa valores positivos para el pie y el dividendo esperado.")
            else:
                # Añadir una columna para el arriendo promedio si no existe.
                if "Arriendo Promedio" not in departamentos.columns:
                    # Generar valores ficticios basados en el tamaño del DataFrame
                    departamentos["Arriendo Promedio"] = [500000 + i * 10000 for i in range(len(departamentos))]

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
    else:
        st.error(f"El archivo CSV debe contener las siguientes columnas: {', '.join(expected_columns)}")
        st.write("Columnas faltantes:", [col for col in expected_columns if col not in departamentos.columns])
        st.write("Columnas adicionales:", [col for col in departamentos.columns if col not in expected_columns])

    # Crear una sección de chat para interactuar con el usuario
    if prompt := st.chat_input("¿Qué más te gustaría saber?"):
        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate a response using the OpenAI API.
        response = client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
        )

        # Stream the response to the chat and store it in session state.
        with st.chat_message("assistant"):
            st.markdown(response.choices[0].message['content'])
        st.session_state.messages.append({"role": "assistant", "content": response.choices[0].message['content']})
