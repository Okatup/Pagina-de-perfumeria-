import re
import csv
import json
import pandas as pd
import os

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

def extraer_url_fragrantica(texto):
    """Extrae la URL de Fragrantica de una línea de texto"""
    # Buscar URLs que comiencen con https://www.fragrantica.com/
    match = re.search(r'https://www\.fragrantica\.com/[^\s,;]+', texto)
    if match:
        return match.group(0)
    return None

def leer_csv_personalizado(ruta_csv):
    """Lee el CSV con formato personalizado"""
    datos = []
    
    with open(ruta_csv, 'r', encoding='utf-8', errors='replace') as file:
        for num_linea, linea in enumerate(file, 1):
            try:
                # Buscar la URL de Fragrantica en la línea
                url = extraer_url_fragrantica(linea)
                
                if url:
                    # Extraer el ID del perfume
                    perfume_id = extraer_id_perfume_url(url)
                    
                    if perfume_id:
                        # Crear la URL de la imagen
                        image_url = crear_url_imagen(perfume_id)
                        
                        # Extraer nombre del perfume y marca (para información adicional)
                        partes_url = url.split('/')
                        brand = partes_url[4] if len(partes_url) >= 5 else ""
                        
                        perfume_info = partes_url[5].split('-') if len(partes_url) >= 6 else []
                        perfume_name = '-'.join(perfume_info[:-1]) if perfume_info else ""
                        
                        # Crear un registro para este perfume
                        perfume = {
                            'url': url,
                            'perfume_id': perfume_id,
                            'brand': brand,
                            'perfume_name': perfume_name,
                            'image_url': image_url
                        }
                        datos.append(perfume)
                        
                        # Mostrar progreso cada 1000 registros
                        if num_linea % 1000 == 0:
                            print(f"Procesadas {num_linea} líneas, encontrados {len(datos)} perfumes")
            except Exception as e:
                print(f"Error en línea {num_linea}: {str(e)}")
                if num_linea % 1000 == 0:  # Solo mostrar algunos errores para no saturar la consola
                    print(f"Línea problemática: {linea[:100]}...")  # Mostrar los primeros 100 caracteres
    
    print(f"Total de perfumes con IDs válidos: {len(datos)}")
    return pd.DataFrame(datos)

def procesar_csv_perfumes(ruta_csv_entrada):
    # Directorio para guardar los archivos de salida
    directorio_salida = os.path.dirname(ruta_csv_entrada)
    base_nombre = os.path.splitext(os.path.basename(ruta_csv_entrada))[0]
    ruta_csv_salida = os.path.join(directorio_salida, f"{base_nombre}_con_imagenes.csv")
    ruta_json_salida = os.path.join(directorio_salida, f"{base_nombre}_con_imagenes.json")
    
    # Leer el CSV utilizando nuestro método personalizado
    print("Leyendo el archivo CSV y extrayendo IDs de perfumes...")
    df = leer_csv_personalizado(ruta_csv_entrada)
    print(f"Se han procesado {len(df)} perfumes con URLs e IDs válidos.")
    
    # Verificar si tenemos datos
    if len(df) == 0:
        print("No se encontraron URLs válidas en el archivo.")
        return None
    
    # Guardar los resultados
    df.to_csv(ruta_csv_salida, sep=';', index=False, encoding='utf-8')
    df.to_json(ruta_json_salida, orient='records')
    
    print(f"\nProceso completado. Archivos guardados en:")
    print(f"CSV: {ruta_csv_salida}")
    print(f"JSON: {ruta_json_salida}")
    
    return df

if __name__ == "__main__":
    # Ruta del archivo CSV de entrada
    ruta_csv = r"C:\Users\lucia\Downloads\Perfume-scrap\fra_perfumes.csv"
    
    # Verificar que el archivo existe
    if not os.path.exists(ruta_csv):
        print(f"Error: El archivo {ruta_csv} no existe.")
    else:
        # Procesar el CSV
        df_resultado = procesar_csv_perfumes(ruta_csv)
        
        if df_resultado is not None:
            # Mostrar algunos ejemplos
            print("\nEjemplos de resultados:")
            print(df_resultado[['url', 'perfume_id', 'image_url']].head(5))
            
            # Verificar que todos tienen URL de imagen
            total = len(df_resultado)
            con_imagen = df_resultado['image_url'].notna().sum()
            
            print(f"\nEstadísticas:")
            print(f"Total de perfumes procesados: {total}")
            print(f"Perfumes con URL de imagen: {con_imagen} ({con_imagen/total*100:.2f}%)")