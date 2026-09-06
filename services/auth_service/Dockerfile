#elije la imagen base de python
FROM python:3.9-slim
#elije la direccion de trabajo dentro del contenedor
WORKDIR /app
#copiar el archivo de requerimientos al contenedor
COPY requirements.txt .
#instalar las dependencias necesarias
RUN pip install --no-cache-dir -r requirements.txt
#copiar el resto de los archivos al contenedor
COPY . .
#comando para ejecutar la aplicacion
CMD ["python", "auth.py"]