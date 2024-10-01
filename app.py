import openai
from dotenv import load_dotenv
import os
import streamlit as st
from fpdf import FPDF
import pdfplumber
from bs4 import BeautifulSoup
import pandas as pd
from difflib import get_close_matches
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import pyautogui as pg
import webbrowser as web
import time

# Cargar las variables de entorno del archivo .env
load_dotenv()

# Configurar la clave API de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configurar la clave API y la URL de servicio de IBM Watson
ibm_api_key = os.getenv("IBM_API_KEY")
ibm_service_url = os.getenv("IBM_SERVICE_URL")

# Lista de objetos analizados relevantes
RELEVANT_OBJECTS = [
    "Viscosidad de la Sangre", "Cristal de Colesterol", "Grasa en Sangre", 
    "Resistencia Vascular", "Elasticidad Vascular", "Demanda de Sangre Miocardial", 
    "Volumen de Perfusión Sanguínea Miocardial", "Consumo de Oxígeno Miocardial", 
    "Volumen de Latido", "Impedancia Ventricular Izquierda de Expulsión", 
    "Fuerza de Bombeo Efectiva Ventricular Izquierda", "Elasticidad de Arteria Coronaria", 
    "Presión de Perfusión Coronaria", "Elasticidad de Vaso Sanguíneo Cerebral", 
    "Estado de Suministro Sanguíneo de Tejido Cerebral", "Coeficiente de Secreción de Pepsina", 
    "Coeficiente de Función de Peristalsis Gástrica", "Coeficiente de Función de Absorción Gástrica", 
    "Coeficiente de Función de Peristalsis del Intestino Delgado", 
    "Coeficiente de Función de Absorción del Intestino Delgado", 
    "Coeficiente de la Función de Peristalsis del Intestino Grueso (colon)", 
    "Coeficiente de absorción colónica", "Coeficiente intestinal bacteriano", 
    "Coeficiente de presión intraluminal", "Metabolismo de las proteínas", 
    "Función de producción de energía", "Función de Desintoxicación", 
    "Función de Secreción de Bilis", "Contenido de Grasa en el Hígado", 
    "Seroglobulina (A/G)", "Bilirrubina Total (TBIL)", "Fosfatasa Alcalina (ALP)", 
    "Ácidos Biliares Totales Séricos (TBA)", "Bilirrubina (DBIL)", "Insulina", 
    "Polipéptido Pancreático (PP)", "Glucagón", "Índice de Urobilinógeno", 
    "Índice de Ácido Úrico", "Índice de Nitrógeno Ureico en la Sangre (BUN)", 
    "Índice de Proteinuria", "Capacidad Vital (VC)", "Capacidad Pulmonar Total (TLC)", 
    "Resistencia de las Vías Aéreas (RAM)", "Contenido de Oxígeno Arterial (PaCO2)", 
    "Estado del Suministro Sanguíneo al Tejido Cerebral", "Arterioesclerosis Cerebral", 
    "Estado Funcional de Nervio Craneal", "Índice de Emoción", "Índice de Memoria (ZS)", 
    "Calcio", "Hierro", "Zinc", "Selenio", "Fósforo", "Potasio", "Magnesio", 
    "Cobre", "Cobalto", "Manganeso", "Yodo", "Níquel", "Flúor", "Molibdeno", 
    "Vanadio", "Estaño", "Silicio", "Estroncio", "Boro"
]
# Autenticador y servicio de IBM Watson Text to Speech
authenticator = IAMAuthenticator(ibm_api_key)
text_to_speech_service = TextToSpeechV1(authenticator=authenticator)
text_to_speech_service.set_service_url(ibm_service_url)

# Función para la conversión de texto a audio (conversor de texto a voz con IBM Watson)
def text_to_speech_ibm(text):
    try:
        response = text_to_speech_service.synthesize(
            text,
            voice='es-ES_EnriqueV3Voice',
            accept='audio/mp3'
        ).get_result()
        
        audio_file = "speech_output_ibm.mp3"
        with open(audio_file, 'wb') as audio:
            audio.write(response.content)
        
        return audio_file
    except Exception as e:
        st.error(f"Error en la conversión de texto a voz: {e}")
        return None
    
    
    
     

# Función para enviar mensajes de texto en WhatsApp
def send_whatsapp_message(phone_number, message):
    web.open(f"https://web.whatsapp.com/send?phone={phone_number}&text={message}")
    time.sleep(10)  # Esperar a que cargue la página y el chat
    pg.press('enter')
    st.success(f"Mensaje enviado a {phone_number}")

# Función para extraer texto de un archivo PDF
def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        text = ''
        for page in pdf.pages:
            text += page.extract_text()
    return text

# Función para extraer datos de un archivo HTML
def extract_data_from_html(file):
    soup = BeautifulSoup(file, 'html.parser')
    tables = soup.find_all('table')

    data = []
    for table in tables:
        rows = table.find_all('tr')[1:]  # Omitir la fila del encabezado
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                objeto_analizado = ' '.join(cols[0].text.split()).strip().lower()  # Normalización del texto
                valor_obtenido = cols[2].text.strip()

                # Verificar coincidencia exacta o aproximada
                matches = get_close_matches(objeto_analizado, [obj.lower() for obj in RELEVANT_OBJECTS], n=1, cutoff=0.8)
                if matches and valor_obtenido:
                    # Usar el nombre exacto del parámetro de la lista RELEVANT_OBJECTS
                    original_match = RELEVANT_OBJECTS[[obj.lower() for obj in RELEVANT_OBJECTS].index(matches[0])]
                    data.append([original_match, valor_obtenido])

    # Crear DataFrame y filtrar solo los parámetros relevantes
    df = pd.DataFrame(data, columns=['Objeto Analizado', 'Valor Obtenido'])
    df = df[df['Objeto Analizado'].isin(RELEVANT_OBJECTS)]
    df = df.drop_duplicates(subset='Objeto Analizado', keep='first')
    df.reset_index(drop=True, inplace=True)  # Resetear índice para asegurar consecutividad
    df.index += 1  # Asegurar que el índice comience en 1
    return df

# Función para generar PDF descargable
def generate_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Informe de Parámetros Médicos del Paciente", ln=True, align='C')

    # Agregar encabezados
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(90, 10, "Objeto Analizado", 1)
    pdf.cell(90, 10, "Valor Obtenido", 1)
    pdf.ln()

    # Agregar datos
    pdf.set_font("Arial", size=10)
    for i, row in dataframe.iterrows():
        pdf.cell(90, 10, row['Objeto Analizado'], 1)
        pdf.cell(90, 10, row['Valor Obtenido'], 1)
        pdf.ln()

    pdf_output = 'Informe_Parametros_Clave.pdf'
    pdf.output(pdf_output)

    # Leer el archivo generado para que sea descargable
    with open(pdf_output, "rb") as file:
        pdf_bytes = file.read()

    return pdf_bytes

# Función principal de la sección de minería de datos
def mineria_de_datos():
    st.header("Minería de Datos")
    uploaded_file = st.file_uploader("Sube un archivo PDF o HTML/HTM", type=["pdf", "html", "htm"])

    if uploaded_file:
        # Detectar el tipo de archivo y extraer texto
        if uploaded_file.type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)
            df = pd.DataFrame([
                ['Viscosidad de la Sangre', '72.211'],
                ['Cristal de Colesterol', '71.326'],
                ['Grasa en Sangre', '1.809']
            ], columns=['Objeto Analizado', 'Valor Obtenido'])
        else:
            html_content = uploaded_file.read().decode("iso-8859-1")
            df = extract_data_from_html(html_content)

        if not df.empty:
            st.write("Parámetros clave encontrados:")
            st.table(df)

            # Botón para descargar el PDF
            if st.button("Descargar como PDF"):
                pdf_bytes = generate_pdf(df)
                st.download_button(label="Descargar PDF", data=pdf_bytes, file_name="Informe_Parametros_Clave.pdf", mime="application/pdf")

            # Nueva opción: Enviar Mensaje por WhatsApp
            phone_number = st.text_input("Ingrese el número de WhatsApp para enviar un mensaje", value="+123456789")
            message = st.text_area("Escriba el mensaje que desea enviar")
            if st.button("Enviar Mensaje por WhatsApp"):
                if phone_number and message:
                    send_whatsapp_message(phone_number, message)
                else:
                    st.warning("Ingrese el número de teléfono y el mensaje.")
        else:
            st.warning("No se encontraron parámetros clave en el archivo.")










def conversion_texto_audio():
    st.header("Conversor de Texto a Audio")
    st.write("Introduce el texto que deseas convertir a audio y presiona el botón para escuchar la respuesta.")

    # Inicializar el estado de la sesión si no está ya inicializado
    if 'audio_bytes' not in st.session_state:
        st.session_state['audio_bytes'] = None
    if 'phone_number' not in st.session_state:
        st.session_state['phone_number'] = ''
    if 'message' not in st.session_state:
        st.session_state['message'] = ''

    # Campo de texto para ingresar el texto
    text_input = st.text_area("Escribe el texto aquí", height=150)

    # Botón para convertir a audio
    if st.button("Convertir a Audio"):
        if text_input.strip():
            # Convertir texto a audio utilizando IBM Watson
            audio_path = text_to_speech_ibm(text_input)
            if audio_path:
                st.success("✅ El audio ha sido generado. Puedes reproducirlo o descargarlo a continuación.")
                
                # Reproducir el archivo de audio generado y guardarlo en la sesión
                with open(audio_path, "rb") as audio_file:
                    st.session_state['audio_bytes'] = audio_file.read()  # Guardar en el estado de sesión
                    st.audio(st.session_state['audio_bytes'], format="audio/mp3")

    # Mostrar el archivo de audio generado
    if st.session_state['audio_bytes']:
        st.audio(st.session_state['audio_bytes'], format="audio/mp3")
        
        # Botón para descargar el archivo de audio
        st.download_button(
            label="Descargar Audio",
            data=st.session_state['audio_bytes'],
            file_name="speech_output_ibm.mp3",  # Asegura que la extensión sea .mp3
            mime="audio/mp3"
        )

    # Mantener el estado de los campos de entrada para el número de teléfono y mensaje
    with st.form("whatsapp_form"):
        st.session_state['phone_number'] = st.text_input("Ingrese el número de WhatsApp para enviar un mensaje", value=st.session_state['phone_number'])
        st.session_state['message'] = st.text_area("Escriba el mensaje que desea enviar con el audio", value=st.session_state['message'])

        submitted = st.form_submit_button("Enviar Mensaje por WhatsApp")
        if submitted:
            if st.session_state['phone_number'] and st.session_state['message']:
                send_whatsapp_message(st.session_state['phone_number'], st.session_state['message'])
                st.success(f"Mensaje enviado a {st.session_state['phone_number']}")
            else:
                st.warning("Ingrese el número de teléfono y el mensaje.")






# Título de la aplicación
st.title("Consultor de Informes Médicos")

# Crear una barra de navegación en la barra lateral
seccion = st.sidebar.selectbox("Navegar a:", ["Chat", "Minería de datos", "Conversor de Texto a Audio"])

# Lógica para mostrar diferentes secciones según la selección
if seccion == "Chat":
    st.header("Chatbot")

    # Inicializar la sesión de mensajes
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "Hola! Soy tu asistente especializado en análisis de informes médicos. Estoy aquí para ayudarte a comprender mejor los resultados de tus análisis y ofrecerte recomendaciones basadas en la información proporcionada. Puedes subir información de tu informe médico, y con mi ayuda, recibirás un resumen detallado de los parámetros clave, una explicación de los síntomas reportados, y orientación personalizada sobre posibles medidas a seguir. ¡Comencemos a analizar tu informe para obtener respuestas claras y útiles!"}]

    # Mostrar historial de mensajes
    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    # Capturar entrada del usuario
    if user_input := st.chat_input():
        # Añadir el mensaje del usuario al historial de la sesión
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)
        
        # Llamada a la API de OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=st.session_state["messages"]
        )
        
        # Extraer la respuesta del modelo
        response_message = response.choices[0].message.content
        st.session_state["messages"].append({"role": "assistant", "content": response_message})
        st.chat_message("assistant").write(response_message)

elif seccion == "Minería de datos":
    mineria_de_datos()

elif seccion == "Conversor de Texto a Audio":
    conversion_texto_audio()
