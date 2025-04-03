import pandas as pd
import os
import json
import re

def extraer_id_perfume_url(url):
    """Extrae el ID del perfume de la URL de Fragrantica"""
    # Patrón para encontrar el ID numérico al final de la URL
    # Ejemplo: https://www.fragrantica.com/perfume/Brand/Perfume-Name-12345.html
    match = re.search(r'-(\d+)\.html$', url)
    if match:
        return match.group(1)  # Devuelve solo el número (grupo 1 del regex)
    return None

def crear_url_imagen(perfume_id):
    """Crea la URL de la imagen basada en el ID del perfume"""
    if perfume_id:
        return f"https://fimgs.net/mdimg/perfume/375x500.{perfume_id}.jpg"
    return None

def normalizar_url(url):
    """Normaliza la URL para facilitar la comparación"""
    if pd.isna(url):
        return None
    # Eliminar espacios en blanco y convertir a minúsculas
    url = url.strip().lower()
    # Asegurarse de que termina con .html si es una URL de Fragrantica
    if "fragrantica.com" in url and not url.endswith(".html"):
        url = url + ".html"
    return url

def combinar_datos_perfume(ruta_csv_datos, ruta_csv_imagenes, ruta_csv_salida):
    """
    Combina los datos de perfumes con las URLs de imágenes, generando directamente
    las URLs de imágenes a partir de los IDs de los perfumes en las URLs.
    
    Args:
        ruta_csv_datos: Ruta al CSV con los datos completos de perfumes
        ruta_csv_imagenes: Ruta al CSV con las URLs de imágenes (como referencia)
        ruta_csv_salida: Ruta donde guardar el CSV combinado
    """
    print(f"Leyendo archivo de datos: {ruta_csv_datos}")
    try:
        # Leer el CSV con los datos completos
        df_datos = pd.read_csv(ruta_csv_datos, sep=';', encoding='utf-8')
        print(f"Columnas en df_datos: {df_datos.columns.tolist()}")
        print(f"Número de registros en df_datos: {len(df_datos)}")
    except Exception as e:
        print(f"Error al leer el archivo de datos: {str(e)}")
        # Intentar con otra codificación si falla
        try:
            df_datos = pd.read_csv(ruta_csv_datos, sep=';', encoding='latin1')
            print(f"Archivo leído con codificación latin1.")
        except Exception as e2:
            print(f"Error al leer el archivo con codificación alternativa: {str(e2)}")
            return

    # Verificar que tiene la columna 'url'
    if 'url' not in df_datos.columns:
        print(f"Error: El archivo de datos no tiene la columna 'url'.")
        return

    # Extraer el ID directamente de la URL y generar URL de imagen
    print("Generando URLs de imágenes a partir de los IDs de perfumes...")
    df_datos['perfume_id'] = df_datos['url'].apply(extraer_id_perfume_url)
    df_datos['image_url'] = df_datos['perfume_id'].apply(crear_url_imagen)
    
    # Contar cuántos registros tienen image_url
    con_imagen = df_datos['image_url'].notna().sum()
    print(f"Registros con URL de imagen: {con_imagen} de {len(df_datos)} ({con_imagen/len(df_datos)*100:.2f}%)")

    # Guardar el resultado en CSV
    print(f"Guardando resultado en CSV: {ruta_csv_salida}")
    df_datos.to_csv(ruta_csv_salida, sep=';', index=False, encoding='utf-8')
    
    # Guardar el resultado en JSON con formato bonito (indentado)
    ruta_json_salida = ruta_csv_salida.replace('.csv', '.json')
    print(f"Guardando resultado en JSON: {ruta_json_salida}")
    
    # Convertir DataFrame a lista de diccionarios
    registros = df_datos.to_dict(orient='records')
    
    # Guardar como JSON con indentación
    with open(ruta_json_salida, 'w', encoding='utf-8') as f:
        json.dump(registros, f, ensure_ascii=False, indent=4)
    
    print("¡Proceso completado!")
    return df_datos

if __name__ == "__main__":
    # Definir rutas de archivos
    directorio = r"C:\Users\lucia\Downloads\Perfume-scrap"
    ruta_csv_datos = os.path.join(directorio, "fra_cleaned.csv")
    ruta_csv_imagenes = os.path.join(directorio, "fra_perfumes_con_imagenes.csv")
    ruta_csv_salida = os.path.join(directorio, "fra_cleaned_images.csv")
    
    # Verificar que los archivos existen
    for ruta, nombre in [(ruta_csv_datos, "Datos"), (ruta_csv_imagenes, "Imágenes")]:
        if not os.path.exists(ruta):
            print(f"Error: El archivo {nombre} no existe en la ruta: {ruta}")
            exit(1)
    
    # Ejecutar la combinación
    df_resultado = combinar_datos_perfume(ruta_csv_datos, ruta_csv_imagenes, ruta_csv_salida)
    
    # Mostrar algunas filas de ejemplo del resultado
    if df_resultado is not None:
        print("\nEjemplo de los primeros registros del resultado:")
        print(df_resultado[['url', 'Perfume', 'Brand', 'perfume_id', 'image_url']].head(3))
        
        # Mostrar información de los archivos generados
        csv_size = os.path.getsize(ruta_csv_salida) / (1024 * 1024)  # Tamaño en MB
        json_size = os.path.getsize(ruta_csv_salida.replace('.csv', '.json')) / (1024 * 1024)  # Tamaño en MB
        print(f"\nArchivos generados:")
        print(f"CSV: {ruta_csv_salida} ({csv_size:.2f} MB)")
        print(f"JSON: {ruta_csv_salida.replace('.csv', '.json')} ({json_size:.2f} MB)")