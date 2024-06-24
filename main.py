from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import pdfplumber
import io
import os
import tempfile
import base64
import json
import datetime

app = FastAPI()

# Configura CORS para permitir acceso desde cualquier dominio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puedes reemplazar "*" con los dominios específicos que deseas permitir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI()

@app.post("/pdf_images")
async def pdf_images(file: UploadFile):
    temp_dir = tempfile.mkdtemp(prefix= file.filename[0:-4])
    try:
        with pdfplumber.open(io.BytesIO(await file.read())) as pdf:
            images = []
            for i, page in enumerate(pdf.pages):
                img = page.to_image(resolution=100)  # Ajusta la resolución según tus necesidades
                img_path = os.path.join(temp_dir, f"page_{i + 1}.png")  
                img.save(img_path)
                images.append(FileResponse(img_path))
            # print(images[0])
            # Devuelve las rutas de los archivos de imágenes
            return images
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
@app.post('/pdf_gpt')
async def pdf_gpt(file: UploadFile):
    
    temp_dir = tempfile.mkdtemp(prefix= f"{file.filename[0:-4]}_[{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}]_")
    try:
        with pdfplumber.open(io.BytesIO(await file.read())) as pdf:
            images = []
            for i, page in enumerate(pdf.pages[0:3]):
                img = page.to_image(resolution=150)  # Ajusta la resolución según tus necesidades
                img_path = os.path.join(temp_dir, f"page_{i + 1}.png")  
                img.save(img_path)
                # Convierte la imagen a bytes
                with open(img_path, "rb") as img_file:
                    img_bytes = img_file.read()

                    # Codifica los bytes en base64
                    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                    images.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        })
            # print(images[0])
            response = client.chat.completions.create(
                    model="gpt-4o",
                    response_format={ "type": "json_object" },
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres un abogado analista de documentos judiciales."
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                "type": "text",
                                "text": "Quiero obtener una respuesta en formato JSON de la siguiente \
                                    informacion: juez, tribunal, imputados, delitos, perjuicio, texto_edicto, \
                                        art_edicto (referencia del articulo para publicación de edictos), acto_judicial, \
                                            fecha_acto_judicial (formato: yyyy-mm-dd), hora_acto_judicial, rubrica. \
                                                Donde 'texto_edicto' es el texto completo del documento \
                                                    (se encuentra después de la primera firma del documento, \
                                                        normalmente inicia mencionando el juez quien pide la publicación del edicto y no incluyas saltos de línea) \
                                                        y 'rubrica' es la rubrica de quienes extienden el documento o se vieron involucrados \
                                                            en el documento con el siguiente formato 'Rubrica de la persona'\
                                                                (como por ejemplo 'J.J. Corver')/'Cargo'. Los nombres deben ser capitalizado.",
                                },
                                *images
                            ],
                        }
                    ],
                    temperature='0',
                )
            # messages=[
            #         {
            #             "role": "system",
            #             "content": "Eres un abogado analista de documentos judiciales."
            #         },
            #         {
            #             "role": "user",
            #             "content": [
            #                 {
            #                 "type": "text",
            #                 "text": "Extrae la siguiente informacion: juez, tribunal, imputados, delito, perjuicio, texto_edicto, acto_judicial, fecha_acto_judicial, hora_acto_judicial, rubrica. Donde 'texto_edicto' es el texto completo del documento y 'rubrica' es la rubrica de quienes extienden el documento o se vieron involucrados en el documento con el siguiente formato 'Rubrica de la persona'(como por ejemplo 'J.J. Corver')/'Cargo'. Los nombres deben ser capitalizado.",
            #                 },
            #                 *images
            #             ],
            #         }
            #     ]
            # Devuelve las rutas de los archivos de imágenes
            return json.loads(response.choices[0].message.content)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
@app.post("/text_gpt/")
async def text_gpt(text: str = Form(...)):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "Eres un corrector de ortografía y experto en lenguaje español, \
                        que analiza textos y corrige para que todas las palabras tengan sentido \
                            si el texto dado tiene errores, respetando signos de puntuación y acentuación. \
                                Además experto en reconocimiento de letras o simbolos que un software \
                                    de tipo OCR como tesseract interpreta, para que símbolos \
                                        que posiblemente sean una letra puedan ser entendidos como letras. \
                                            Aunque, no solo analizas las letras individuales, sino que \
                                                también las palabras que esos símbolos pueden formar en \
                                                    conjunto. Devuelves la respuesta en un objeto de tipo \
                                                        JSON con el atributo llamado \"texto_corregido\"."
                },
                {
                    "role": "user",
                    "content": f"Analiza el siguiente texto: {text}"
                }
            ],
            temperature=0,
        )

        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)