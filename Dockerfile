# Usamos una imagen base oficial de Python
FROM python:3.11.9-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# INSTALAMOS LAS DEPENDENCIAS DEL SISTEMA (¡LA PARTE CLAVE!)
RUN apt-get update && apt-get install -y \
    build-essential \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiamos el archivo de requerimientos y los instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de los archivos de la aplicación
COPY . .

# Exponemos el puerto que Gunicorn usará
EXPOSE 10000

# El comando para correr la aplicación (lo toma del Procfile)
CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:10000"]