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
openai_api_key = st.secrets["sk-proj-fw1qCdqAYdEuLwq6cHJRT3BlbkFJ12Hjuv4DEdunGEYT5YJJ"] if "openai_api_key" in st.secrets else None

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
    expected_columns_rent = ["Precio", "Metros Cuadrados", "Dormitorios", "Baños", "Link"]

    # Cargar base de datos de departamentos desde GitHub.
    @st.cache_data
    def load_data(url):
        try:
            data = pd.read_csv(url)
            return data
        except Exception as e:
            st.error(f"Error al cargar los datos: {e}")
            return None

    url_sales = "https://raw.githubusercontent.com/tomasortizi/chatbot-template-6oaq5tmqnp9/main/departamentos_en_venta.csv"
    url_rent = "https://raw.githubusercontent.com/tomasortizi/chatbot-template-6oaq5tmqnp9/main/departamentos_en_arriendo.csv"
    
    departamentos_venta = load_data(url_sales)
    departamentos_arriendo = load_data(url_rent)

    if departamentos_venta is not None and departamentos_arriendo is not None:
        # Validar las columnas del archivo CSV de ventas
        if all(column in departamentos_venta.columns for column in expected_columns):
            # Validar las columnas del archivo CSV de arriendo
            if all(column in departamentos_arriendo.columns for column in expected_columns_rent):
                
                # Asegurarse de que los valores de pie_uf y dividendo_clp sean del mismo tipo que la columna Precio
                if pie_uf is not None and dividendo_clp is not None:
                    try:
                        pie_uf = type(departamentos_venta["Precio"].iloc[0])(pie_uf)
                        dividendo_clp = type(departamentos_venta["Precio"].iloc[0])(dividendo_clp)
                    except ValueError:
                        st.error("Los valores de pie y dividendo no son compatibles con el tipo de datos de los precios en la base de datos.")
                        st.stop()
                else:
                    st.error("Por favor, ingresa valores válidos para el pie y el dividendo esperado.")
                    st.stop()

                # Simulación de tasa de crédito hipotecario (normalmente se obtendría de `www.siii.cl`).
                tasa_credito = 0.048  # 4.8% anual

                def calcular_dividendo(precio, pie, tasa, años=25):
                    monto_credito = precio - pie
                    tasa_mensual = tasa / 12
                    meses = años * 12
                    dividendo = (monto_credito * tasa_mensual) / (1 - (1 + tasa_mensual) ** -meses)
                    return dividendo

                # Añadir columna con valor de arriendo aproximado en UF y UF/m2 al dataset de arriendo
                multiplicador_arriendo = 220
                departamentos_arriendo["Arriendo UF"] = departamentos_arriendo["Precio"] / multiplicador_arriendo
                departamentos_arriendo["UF/m2"] = departamentos_arriendo["Arriendo UF"] / departamentos_arriendo["Metros Cuadrados"]

                # Añadir columna de UF/m2 al dataset de ventas
                departamentos_venta["UF/m2"] = departamentos_venta["Precio"] / departamentos_venta["Metros Cuadrados"]

                # Botón para iniciar la búsqueda de departamentos
                if st.button("Buscar Departamentos"):
                    if pie_uf <= 0 or dividendo_clp <= 0:
                        st.error("Por favor, ingresa valores positivos para el pie y el dividendo esperado.")
                    else:
                        # Calcular dividendo y rentabilidad en el dataset de ventas
                        departamentos_venta["Pie (UF)"] = pie_uf
                        departamentos_venta["Dividendo Mensual (UF)"] = departamentos_venta["Precio"].apply(lambda x: calcular_dividendo(x, pie_uf, tasa_credito))
                        departamentos_venta["Dividendo Mensual (CLP)"] = departamentos_venta["Dividendo Mensual (UF)"] * 37500  # Asumimos UF a CLP es 30,000.

                        # Filtrar y comparar departamentos de arriendo y venta por valores UF/m2 similares
                        resultados_comparativos = []
                        for _, row_venta in departamentos_venta.iterrows():
                            uf_m2_venta = row_venta["UF/m2"]
                            comparables = departamentos_arriendo[
                                departamentos_arriendo["UF/m2"].between(uf_m2_venta * 0.95, uf_m2_venta * 1.05)
                            ]
                            for _, row_arriendo in comparables.iterrows():
                                rentabilidad = ((row_arriendo["Arriendo UF"] - row_venta["Dividendo Mensual (UF)"]) / row_venta["Dividendo Mensual (UF)"]) * 100
                                resultado = {
                                    "Venta Link": row_venta["Link"],
                                    "UF/m2 Venta": uf_m2_venta,
                                    "Dividendo Mensual (UF)": row_venta["Dividendo Mensual (UF)"],
                                    "Rentabilidad (%)": rentabilidad,
                                    "Arriendo Link": row_arriendo["Link"],
                                    "Precio Arriendo": row_arriendo["Precio"],
                                    "Metros Cuadrados Arriendo": row_arriendo["Metros Cuadrados"],
                                    "Dormitorios Arriendo": row_arriendo["Dormitorios"],
                                    "Baños Arriendo": row_arriendo["Baños"],
                                    "Arriendo UF": row_arriendo["Arriendo UF"],
                                    "UF/m2 Arriendo": row_arriendo["UF/m2"]
                                }
                                resultados_comparativos.append(resultado)

                        # Convertir los resultados a un DataFrame
                        resultados_df = pd.DataFrame(resultados_comparativos)

                        # Mostrar resultados.
                        st.write(resultados_df)

                        # Permitir la descarga de los resultados.
                        st.download_button(
                            label="Descargar Resultados",
                            data=resultados_df.to_csv(index=False).encode('utf-8'),
                            file_name='resultados_departamentos_comparativos.csv',
                            mime='text/csv'
                        )
            else:
                st.error(f"El archivo CSV de arriendo debe contener las siguientes columnas: {', '.join(expected_columns_rent)}")
                st.write("Columnas faltantes:", [col for col in expected_columns_rent if col not in departamentos_arriendo.columns])
                st.write("Columnas adicionales:", [col for col in departamentos_arriendo.columns if col not in expected_columns_rent])
        else:
            st.error(f"El archivo CSV de ventas debe contener las siguientes columnas: {', '.join(expected_columns)}")
            st.write("Columnas faltantes:", [col for col in expected_columns if col not in departamentos_venta.columns])
            st.write("Columnas adicionales:", [col for col in departamentos_venta.columns if col not in expected_columns])
    
    # Crear una sección de chat para interactuar con el usuario
    if prompt := st.chat_input("¿Qué más te gustaría saber?"):
        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate a response using the OpenAI API.
        try:
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
        except Exception as e:
            st.error(f"Error al generar respuesta de OpenAI: {e}")
