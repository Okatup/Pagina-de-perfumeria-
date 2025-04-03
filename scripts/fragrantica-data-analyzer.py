import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import re
import os

def load_datasets():
    """Carga los datasets de Fragrantica probando diferentes codificaciones"""
    print("Cargando datasets de Fragrantica...")
    
    # Lista de codificaciones comunes para probar
    encodings = [
        'utf-8', 
        'latin1',      # También conocido como ISO-8859-1
        'iso-8859-1',
        'cp1252',      # Windows-1252
        'utf-16'
    ]
    
    cleaned_df = None
    perfumes_df = None
    
    # Intentar cargar fra_cleaned.csv con diferentes codificaciones
    for encoding in encodings:
        try:
            print(f"Intentando cargar fra_cleaned.csv con codificación {encoding}...")
            cleaned_df = pd.read_csv('fra_cleaned.csv', encoding=encoding, on_bad_lines='skip')
            print(f"¡Éxito! Dataset fra_cleaned.csv cargado con codificación {encoding}")
            break
        except UnicodeDecodeError:
            print(f"Falló con codificación {encoding}")
        except Exception as e:
            print(f"Error al cargar con {encoding}: {str(e)}")
    
    # Intentar cargar fra_perfumes.csv con diferentes codificaciones
    for encoding in encodings:
        try:
            print(f"Intentando cargar fra_perfumes.csv con codificación {encoding}...")
            perfumes_df = pd.read_csv('fra_perfumes.csv', encoding=encoding, on_bad_lines='skip')
            print(f"¡Éxito! Dataset fra_perfumes.csv cargado con codificación {encoding}")
            break
        except UnicodeDecodeError:
            print(f"Falló con codificación {encoding}")
        except Exception as e:
            print(f"Error al cargar con {encoding}: {str(e)}")
    
    if cleaned_df is not None:
        print(f"Dataset fra_cleaned.csv cargado: {cleaned_df.shape[0]} filas, {cleaned_df.shape[1]} columnas")
        print("\nColumnas en fra_cleaned.csv:")
        for col in cleaned_df.columns:
            print(f"  - {col}")
    else:
        print("No se pudo cargar fra_cleaned.csv con ninguna codificación.")
    
    if perfumes_df is not None:
        print(f"Dataset fra_perfumes.csv cargado: {perfumes_df.shape[0]} filas, {perfumes_df.shape[1]} columnas")
        print("\nColumnas en fra_perfumes.csv:")
        for col in perfumes_df.columns:
            print(f"  - {col}")
    else:
        print("No se pudo cargar fra_perfumes.csv con ninguna codificación.")
    
    # Si al menos uno de los datasets se cargó correctamente, continuar
    if cleaned_df is not None or perfumes_df is not None:
        return cleaned_df, perfumes_df
    else:
        # Si no se pudo cargar ninguno, intentar con otra estrategia
        print("\nIntentando cargar con pandas_read_csv con motor Python...")
        try:
            cleaned_df = pd.read_csv('fra_cleaned.csv', engine='python')
            print("¡Éxito con engine='python' para fra_cleaned.csv!")
        except Exception as e:
            print(f"Error con engine='python' para fra_cleaned.csv: {str(e)}")
        
        try:
            perfumes_df = pd.read_csv('fra_perfumes.csv', engine='python')
            print("¡Éxito con engine='python' para fra_perfumes.csv!")
        except Exception as e:
            print(f"Error con engine='python' para fra_perfumes.csv: {str(e)}")
        
        return cleaned_df, perfumes_df

def merge_datasets(cleaned_df, perfumes_df):
    """Combina los datasets si es necesario y posible"""
    
    # Verificar si ambos datasets están disponibles
    if cleaned_df is None or perfumes_df is None:
        print("No se pueden combinar los datasets porque al menos uno no está disponible.")
        # Devolver el que esté disponible
        return cleaned_df if cleaned_df is not None else perfumes_df
    
    # Verificar si hay una columna común para unir los datasets
    common_cols = set(cleaned_df.columns) & set(perfumes_df.columns)
    print(f"\nColumnas comunes entre los datasets: {common_cols}")
    
    if 'id' in common_cols or 'perfume_id' in common_cols or 'url' in common_cols:
        # Identificar la columna clave para la unión
        join_col = 'id' if 'id' in common_cols else ('perfume_id' if 'perfume_id' in common_cols else 'url')
        
        print(f"Uniendo datasets usando la columna '{join_col}'...")
        
        # Unir datasets
        merged_df = pd.merge(
            cleaned_df, 
            perfumes_df, 
            on=join_col, 
            how='outer',  # outer join para mantener todos los datos
            suffixes=('', '_perfumes')
        )
        
        print(f"Dataset combinado: {merged_df.shape[0]} filas, {merged_df.shape[1]} columnas")
        return merged_df
    else:
        print("No se encontraron columnas comunes óptimas para unir los datasets.")
        print("Continuando el análisis con el dataset más completo.")
        # Elegir el dataset con más filas
        if cleaned_df.shape[0] >= perfumes_df.shape[0]:
            print(f"Usando cleaned_df con {cleaned_df.shape[0]} filas.")
            return cleaned_df
        else:
            print(f"Usando perfumes_df con {perfumes_df.shape[0]} filas.")
            return perfumes_df

def explore_dataset(df, name):
    """Explora un dataset para entender su estructura y contenido"""
    print(f"\n=== Exploración del dataset {name} ===")
    
    # Información básica
    print(f"Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
    
    # Tipos de datos
    print("\nTipos de datos:")
    print(df.dtypes)
    
    # Valores nulos
    print("\nValores nulos por columna:")
    null_counts = df.isnull().sum()
    for col, count in null_counts.items():
        if count > 0:
            print(f"  - {col}: {count} ({count/len(df)*100:.2f}%)")
    
    # Estadísticas descriptivas para columnas numéricas
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        print("\nEstadísticas para columnas numéricas:")
        print(df[numeric_cols].describe())
    
    # Valores únicos para columnas categóricas (limitado a las primeras 5 columnas para no saturar)
    cat_cols = df.select_dtypes(include=['object']).columns[:5]
    if len(cat_cols) > 0:
        print("\nValores únicos en columnas categóricas:")
        for col in cat_cols:
            unique_count = df[col].nunique()
            print(f"  - {col}: {unique_count} valores únicos")
            if unique_count < 10:  # Mostrar solo si hay pocos valores únicos
                print(f"    Valores: {df[col].unique()}")
    
    return

def analyze_seasonal_data(df):
    """Analiza datos de temporadas en perfumes"""
    # Identificar columnas de temporadas
    season_cols = [col for col in df.columns if col.lower() in ['spring', 'summer', 'fall', 'winter', 'primavera', 'verano', 'otoño', 'invierno']]
    
    if not season_cols:
        # Buscar columnas que puedan contener datos de temporadas
        potential_cols = [col for col in df.columns if 'season' in col.lower()]
        if potential_cols:
            print(f"\nNo se encontraron columnas estándar de temporadas, pero hay columnas potenciales: {potential_cols}")
            season_cols = potential_cols
        else:
            print("\nNo se encontraron datos de temporadas en el dataset.")
            return None
    
    print(f"\n=== Análisis de temporadas ===")
    print(f"Columnas de temporadas encontradas: {season_cols}")
    
    # Convertir a valores numéricos si es necesario
    for col in season_cols:
        if df[col].dtype == 'object':
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                print(f"Columna {col} convertida a numérica.")
            except:
                print(f"No se pudo convertir {col} a valores numéricos.")
    
    # Calcular promedios por temporada
    season_data = {}
    for col in season_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            mean_val = df[col].mean()
            season_data[col] = mean_val
            print(f"Promedio para {col}: {mean_val:.2f}")
    
    # Visualizar datos por temporada
    if season_data:
        plt.figure(figsize=(10, 6))
        sns.barplot(x=list(season_data.keys()), y=list(season_data.values()))
        plt.title('Puntuación promedio por temporada')
        plt.ylabel('Puntuación')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('seasonal_ratings.png')
        print("Gráfico guardado como 'seasonal_ratings.png'")
        
        # Encontrar los mejores perfumes por temporada
        best_perfumes = {}
        for season in season_cols:
            if pd.api.types.is_numeric_dtype(df[season]):
                # Identificar columnas para mostrar en resultados
                display_cols = []
                for col in ['name', 'title', 'brand', 'perfume_name']:
                    if col in df.columns:
                        display_cols.append(col)
                
                # Añadir la columna de temporada
                display_cols.append(season)
                
                # Verificar si hay columnas para mostrar
                if not display_cols:
                    print(f"No se encontraron columnas adecuadas para mostrar los mejores perfumes para {season}")
                    continue
                
                # Ordenar y obtener los mejores
                top_perfumes = df.sort_values(by=[season], ascending=False).head(10)
                best_perfumes[season] = top_perfumes[display_cols].to_dict('records')
                
                print(f"\nTop 3 perfumes para {season}:")
                for i, perfume in enumerate(best_perfumes[season][:3], 1):
                    name_col = next((col for col in ['name', 'title', 'perfume_name'] if col in perfume), None)
                    if name_col:
                        print(f"{i}. {perfume[name_col]} - Puntuación: {perfume[season]:.2f}")
        
        return best_perfumes
    
    return None

def extract_notes_data(df):
    """Extrae y analiza datos de notas olfativas"""
    # Identificar columnas que pueden contener notas
    notes_cols = [col for col in df.columns if 'note' in col.lower() or 'notes' in col.lower() or 'accord' in col.lower()]
    
    if not notes_cols:
        print("\nNo se encontraron columnas específicas de notas olfativas.")
        return None
    
    print(f"\n=== Análisis de notas olfativas ===")
    print(f"Columnas relacionadas con notas: {notes_cols}")
    
    # Procesar notas y contabilizar frecuencias
    all_notes = []
    
    for col in notes_cols:
        for notes_text in df[col].dropna():
            if isinstance(notes_text, str):
                # Intentar extraer notas del texto
                # Primero ver si es JSON
                try:
                    notes_dict = json.loads(notes_text)
                    for note in notes_dict.keys():
                        all_notes.append(note)
                except:
                    # Si no es JSON, intentar separar por comas, punto y coma, etc.
                    for separator in [',', ';', '|', '\n']:
                        if separator in notes_text:
                            notes_list = [note.strip() for note in notes_text.split(separator)]
                            all_notes.extend(notes_list)
                            break
    
    if not all_notes:
        print("No se pudieron extraer notas del dataset.")
        return None
    
    # Contabilizar frecuencia de notas
    note_counter = Counter(all_notes)
    
    # Mostrar las notas más comunes
    print("\nNotas más comunes:")
    for note, count in note_counter.most_common(15):
        print(f"  - {note}: {count} veces")
    
    # Visualizar las notas más comunes
    top_notes = dict(note_counter.most_common(15))
    plt.figure(figsize=(12, 8))
    sns.barplot(x=list(top_notes.keys()), y=list(top_notes.values()))
    plt.title('Notas más comunes en perfumes')
    plt.xlabel('Nota')
    plt.ylabel('Frecuencia')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('common_notes.png')
    print("Gráfico guardado como 'common_notes.png'")
    
    # Crear un dataset de notas
    notes_data = {
        'note_counts': dict(note_counter),
        'top_notes': dict(note_counter.most_common(30))
    }
    
    return notes_data

def analyze_ratings_by_gender(df):
    """Analiza ratings por género si está disponible"""
    # Comprobar si hay columna de género
    gender_cols = [col for col in df.columns if 'gender' in col.lower() or 'sex' in col.lower()]
    rating_cols = [col for col in df.columns if 'rating' in col.lower() or 'score' in col.lower() or 'vote' in col.lower()]
    
    if not gender_cols or not rating_cols:
        print("\nNo se encontraron datos suficientes para analizar ratings por género.")
        return None
    
    gender_col = gender_cols[0]
    rating_col = rating_cols[0]
    
    print(f"\n=== Análisis de ratings por género ===")
    print(f"Usando columnas: {gender_col} y {rating_col}")
    
    # Convertir ratings a numérico si es necesario
    if df[rating_col].dtype == 'object':
        try:
            df[rating_col] = pd.to_numeric(df[rating_col], errors='coerce')
        except:
            print(f"No se pudo convertir {rating_col} a valores numéricos.")
            return None
    
    # Agrupar por género y calcular promedios
    if pd.api.types.is_numeric_dtype(df[rating_col]):
        gender_ratings = df.groupby(gender_col)[rating_col].agg(['mean', 'count']).reset_index()
        print("\nRatings promedio por género:")
        print(gender_ratings)
        
        # Visualizar
        plt.figure(figsize=(10, 6))
        sns.barplot(x=gender_col, y='mean', data=gender_ratings, hue=gender_col, legend=False)
        plt.title('Rating promedio por género')
        plt.xlabel('Género')
        plt.ylabel(f'Rating promedio ({rating_col})')
        plt.tight_layout()
        plt.savefig('gender_ratings.png')
        print("Gráfico guardado como 'gender_ratings.png'")
        
        # Encontrar los perfumes mejor calificados por género
        best_by_gender = {}
        for gender in df[gender_col].dropna().unique():
            gender_df = df[df[gender_col] == gender]
            
            # Columnas para mostrar
            display_cols = []
            for col in ['name', 'title', 'brand', 'perfume_name']:
                if col in df.columns:
                    display_cols.append(col)
            
            display_cols.append(rating_col)
            if gender_col not in display_cols:
                display_cols.append(gender_col)
            
            top_perfumes = gender_df.sort_values(by=[rating_col], ascending=False).head(5)
            best_by_gender[gender] = top_perfumes[display_cols].to_dict('records')
        
        return best_by_gender
    
    return None

def prepare_perfumes_database(df):
    """Prepara una base de datos unificada de perfumes"""
    print("\n=== Preparando base de datos unificada de perfumes ===")
    
    # Identificar columnas clave
    essential_columns = []
    
    # Identificar columnas de nombre/título
    name_cols = [col for col in df.columns if col.lower() in ['name', 'title', 'perfume_name']]
    if name_cols:
        essential_columns.append(name_cols[0])
        print(f"Columna de nombre: {name_cols[0]}")
    
    # Identificar columna de marca
    brand_cols = [col for col in df.columns if 'brand' in col.lower()]
    if brand_cols:
        essential_columns.append(brand_cols[0])
        print(f"Columna de marca: {brand_cols[0]}")
    
    # Identificar columna de rating
    rating_cols = [col for col in df.columns if 'rating' in col.lower() or 'score' in col.lower()]
    if rating_cols:
        essential_columns.append(rating_cols[0])
        print(f"Columna de rating: {rating_cols[0]}")
    
    # Identificar columnas de temporadas
    season_cols = [col for col in df.columns if col.lower() in ['spring', 'summer', 'fall', 'winter', 'primavera', 'verano', 'otoño', 'invierno']]
    if season_cols:
        essential_columns.extend(season_cols)
        print(f"Columnas de temporadas: {season_cols}")
    
    # Identificar columna de género
    gender_cols = [col for col in df.columns if 'gender' in col.lower() or 'sex' in col.lower()]
    if gender_cols:
        essential_columns.append(gender_cols[0])
        print(f"Columna de género: {gender_cols[0]}")
    
    # Identificar columnas de notas
    notes_cols = [col for col in df.columns if 'note' in col.lower() or 'notes' in col.lower() or 'accord' in col.lower()]
    if notes_cols:
        essential_columns.append(notes_cols[0])
        print(f"Columna principal de notas: {notes_cols[0]}")
    
    # Crear dataset simplificado con las columnas esenciales
    if essential_columns:
        # Asegurarse de que las columnas existen en el dataframe
        valid_cols = [col for col in essential_columns if col in df.columns]
        if not valid_cols:
            print("No se encontraron columnas válidas para la base de datos.")
            return None
        
        clean_df = df[valid_cols].copy()
        
        # Renombrar columnas para estandarización si es necesario
        column_mapping = {}
        
        # Estandarizar nombre
        if name_cols and name_cols[0] != 'name':
            column_mapping[name_cols[0]] = 'name'
        
        # Estandarizar marca
        if brand_cols and brand_cols[0] != 'brand':
            column_mapping[brand_cols[0]] = 'brand'
        
        # Estandarizar rating
        if rating_cols and rating_cols[0] != 'rating':
            column_mapping[rating_cols[0]] = 'rating'
        
        # Estandarizar género
        if gender_cols and gender_cols[0] != 'gender':
            column_mapping[gender_cols[0]] = 'gender'
        
        # Estandarizar notas
        if notes_cols and notes_cols[0] != 'notes':
            column_mapping[notes_cols[0]] = 'notes'
        
        # Aplicar renombrado
        if column_mapping:
            clean_df = clean_df.rename(columns=column_mapping)
            print(f"\nColumnas renombradas: {column_mapping}")
        
        # Limpiar valores nulos
        clean_df = clean_df.fillna({
            'rating': 0,
            'brand': 'Desconocido',
            'gender': 'Unisex'
        })
        
        # Convertir ratings a numérico si es necesario
        if 'rating' in clean_df.columns and clean_df['rating'].dtype == 'object':
            try:
                clean_df['rating'] = pd.to_numeric(clean_df['rating'], errors='coerce')
                clean_df['rating'] = clean_df['rating'].fillna(0)
            except:
                print("No se pudo convertir la columna 'rating' a valores numéricos.")
        
        # Convertir temporadas a numérico si es necesario
        for col in season_cols:
            col_name = col if col not in column_mapping else column_mapping[col]
            if col_name in clean_df.columns and clean_df[col_name].dtype == 'object':
                try:
                    clean_df[col_name] = pd.to_numeric(clean_df[col_name], errors='coerce')
                    clean_df[col_name] = clean_df[col_name].fillna(0)
                except:
                    print(f"No se pudo convertir la columna '{col_name}' a valores numéricos.")
        
        print(f"\nBase de datos unificada creada con {len(clean_df)} perfumes y {len(clean_df.columns)} atributos.")
        return clean_df
    
    print("No se pudieron identificar columnas esenciales para la base de datos.")
    return None

def save_recommendations(seasonal_data, notes_data, gender_data, output_dir='.'):
    """Guarda los datos de recomendaciones en archivos JSON"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Guardar recomendaciones por temporada
    if seasonal_data:
        with open(os.path.join(output_dir, 'seasonal_recommendations.json'), 'w', encoding='utf-8') as f:
            json.dump(seasonal_data, f, ensure_ascii=False, indent=4)
        print("Recomendaciones por temporada guardadas en 'seasonal_recommendations.json'")
    
    # Guardar datos de notas
    if notes_data:
        with open(os.path.join(output_dir, 'notes_data.json'), 'w', encoding='utf-8') as f:
            json.dump(notes_data, f, ensure_ascii=False, indent=4)
        print("Datos de notas guardados en 'notes_data.json'")
    
    # Guardar recomendaciones por género
    if gender_data:
        with open(os.path.join(output_dir, 'gender_recommendations.json'), 'w', encoding='utf-8') as f:
            json.dump(gender_data, f, ensure_ascii=False, indent=4)
        print("Recomendaciones por género guardadas en 'gender_recommendations.json'")

def save_database(df, output_dir='.'):
    """Guarda la base de datos de perfumes en formatos CSV y JSON"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Guardar en CSV
    csv_path = os.path.join(output_dir, 'perfumes_database.csv')
    df.to_csv(csv_path, index=False)
    print(f"Base de datos guardada en '{csv_path}'")
    
    # Guardar en JSON
    json_path = os.path.join(output_dir, 'perfumes_database.json')
    
    # Intentar guardar en JSON (puede fallar si hay tipos de datos complejos)
    try:
        df.to_json(json_path, orient='records', force_ascii=False, indent=4)
        print(f"Base de datos guardada en '{json_path}'")
    except:
        print("Error al guardar en formato JSON. Intentando método alternativo...")
        # Método alternativo
        records = df.to_dict('records')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=4)
        print(f"Base de datos guardada en '{json_path}' usando método alternativo")

if __name__ == "__main__":
    print("=== Analizador de Datos de Perfumes de Fragrantica ===")
    
    # Cargar datasets
    cleaned_df, perfumes_df = load_datasets()
    
    if cleaned_df is None and perfumes_df is None:
        print("Error al cargar los datasets. Terminando programa.")
        exit(1)
    
    # Combinar datasets si es posible
    working_df = merge_datasets(cleaned_df, perfumes_df)
    
    if working_df is None:
        print("No se pudo crear un dataset de trabajo. Terminando programa.")
        exit(1)
    
    # Explorar dataset
    explore_dataset(working_df, "de trabajo")
    
    # Analizar datos por temporada
    seasonal_data = analyze_seasonal_data(working_df)
    
    # Extraer datos de notas
    notes_data = extract_notes_data(working_df)
    
    # Analizar ratings por género
    gender_data = analyze_ratings_by_gender(working_df)
    
    # Preparar base de datos unificada
    clean_database = prepare_perfumes_database(working_df)
    
    # Guardar recomendaciones
    save_recommendations(seasonal_data, notes_data, gender_data)
    
    # Guardar base de datos
    if clean_database is not None:
        save_database(clean_database)
    
    print("\n¡Análisis completado! Ahora puedes usar los archivos generados para tu aplicación.")