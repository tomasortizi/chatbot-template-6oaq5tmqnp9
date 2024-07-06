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
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    try:
        # Create an OpenAI client.
        client = OpenAI(api_key=openai_api_key)

        # Create a session state variable to store the chat messages. This ensures that the
        # messages persist across reruns.
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Simulación de base de datos de departamentos (normalmente se obtendría de `www.portalinmobiliario.cl`).
        departamentos = pd.DataFrame([
            {"Precio": 5000, "Metros Cuadrados": 60, "Dormitorios": 2, "Baños": 1, "Link": "https://ejemplo1.com"},
            {"Precio": 7000, "Metros Cuadrados": 80, "Dormitorios": 3, "Baños": 2, "Link": "https://ejemplo2.com"},
            # Añadir más departamentos según sea necesario.
        ])

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
                departamentos["Arriendo Promedio"] = [500, 700]  # Valores ficticios.

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


