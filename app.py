import streamlit as st
import pytesseract
from PIL import Image, ImageOps, ImageDraw

st.set_page_config(page_title="Escáner de letras", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
.stApp {
    background-color: #0d1117;
}
[data-testid="stHeader"] {
    background: transparent;
}
section[data-testid="stSidebar"] {
    background-color: #161b22;
}
.stApp p, .stApp label, .stApp li {
    color: #c9f7d5;
}
h1, h2, h3 {
    font-family: 'Share Tech Mono', monospace;
    color: #39ff14 !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
    color: #c9f7d5 !important;
}
[data-testid="stAlert"] {
    background-color: #1c2b22 !important;
    border: 1px solid #39ff14;
}
[data-testid="stAlert"] * {
    color: #c9f7d5 !important;
}
[data-testid="stFileUploaderDropzone"] {
    background-color: #161b22 !important;
    border: 1px dashed #39ff14;
}
[data-testid="stFileUploaderDropzone"] * {
    color: #c9f7d5 !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background-color: #39ff14 !important;
    color: #0d1117 !important;
}
textarea {
    background-color: #161b22 !important;
    color: #c9f7d5 !important;
}
div.stButton > button, div.stDownloadButton > button {
    background-color: #39ff14;
    color: #0d1117 !important;
    border: none;
    border-radius: 4px;
    font-family: 'Share Tech Mono', monospace;
    padding: 8px 24px;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background-color: #c9f7d5;
}
</style>
""", unsafe_allow_html=True)

idiomas = {"Español": "spa", "Inglés": "eng", "Español e inglés": "spa+eng"}

with st.sidebar:
    st.subheader("Cómo funciona")
    st.write("1. Entrega una imagen con texto.")
    st.write("2. Ajusta la imagen si es difícil de leer.")
    st.write("3. El escáner extrae las letras.")
    idioma = st.selectbox("Idioma del texto", list(idiomas.keys()))
    st.subheader("Ajustes de imagen")
    gris = st.checkbox("Escala de grises", value=True)
    contraste = st.checkbox("Mejorar contraste", value=True)
    binarizar = st.checkbox("Blanco y negro puro")
    umbral = st.slider("Umbral", 50, 200, 128, disabled=not binarizar)

st.title("🔍 Escáner de letras")
st.write("Sube una foto con texto y el escáner lo convierte en texto editable.")

modo = st.radio("¿De dónde viene la imagen?", ["Subir imagen", "Tomar foto"], horizontal=True)

if modo == "Subir imagen":
    archivo = st.file_uploader("Imagen con texto", type=["jpg", "jpeg", "png"])
else:
    archivo = st.camera_input("Apunta al texto y toma la foto")

if archivo is not None:
    original = ImageOps.exif_transpose(Image.open(archivo)).convert("RGB")
    procesada = original
    if gris:
        procesada = ImageOps.grayscale(procesada)
    if contraste:
        procesada = ImageOps.autocontrast(procesada)
    if binarizar:
        procesada = ImageOps.grayscale(procesada).point(lambda p: 255 if p > umbral else 0)

    c1, c2 = st.columns(2)
    c1.image(original, caption="Original", use_container_width=True)
    c2.image(procesada, caption="Lo que ve el escáner", use_container_width=True)

    huella = hash(archivo.getvalue())

    if st.button("Escanear"):
        try:
            with st.spinner("Escaneando letras..."):
                texto = pytesseract.image_to_string(procesada, lang=idiomas[idioma])
                datos = pytesseract.image_to_data(procesada, lang=idiomas[idioma], output_type=pytesseract.Output.DICT)
            st.session_state.resultado = {"texto": texto, "datos": datos, "imagen": original, "huella": huella}
        except pytesseract.TesseractNotFoundError:
            st.error("No encuentro Tesseract. Agrega un archivo packages.txt con tesseract-ocr y tesseract-ocr-spa.")
        except Exception as e:
            st.error(f"No se pudo leer la imagen: {e}")

    res = st.session_state.get("resultado")

    if res and res["huella"] == huella:
        st.divider()
        st.header("Resultado")
        texto = res["texto"].strip()
        datos = res["datos"]

        if texto == "":
            st.info("No encontré letras. Prueba con 'Blanco y negro puro' o con una foto más nítida.")
        else:
            confianzas = [float(c) for c, t in zip(datos["conf"], datos["text"]) if t.strip() and float(c) >= 0]
            media = sum(confianzas) / len(confianzas) if confianzas else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("Palabras", len(texto.split()))
            m2.metric("Caracteres", len(texto))
            m3.metric("Confianza", f"{media:.0f}%")

            if media < 60:
                st.warning("El escáner dudó bastante. Revisa el texto o prueba con otros ajustes de imagen.")

            vista = res["imagen"].copy()
            dibujo = ImageDraw.Draw(vista)
            grosor = max(2, vista.width // 300)
            for i, palabra in enumerate(datos["text"]):
                if palabra.strip() and float(datos["conf"][i]) > 40:
                    x, y, w, h = datos["left"][i], datos["top"][i], datos["width"][i], datos["height"][i]
                    dibujo.rectangle([x, y, x + w, y + h], outline="#39ff14", width=grosor)
            st.image(vista, caption="Palabras encontradas", use_container_width=True)

            st.text_area("Texto extraído (puedes editarlo)", value=texto, height=220)
            st.download_button("Descargar texto", texto, file_name="texto.txt")
