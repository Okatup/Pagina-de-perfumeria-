# app.py
from flask import Flask, render_template, request, jsonify
import json
import os
import random
import pandas as pd
import sys

# Ajustar la ruta para encontrar el módulo recommender
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

try:
    from scripts.recommender import PerfumeRecommender
except ImportError:
    print("No se pudo importar PerfumeRecommender, se usará una versión de respaldo")
    class PerfumeRecommender:
        def load_data(self, perfumes):
            return self
        def get_recommendations(self, preferences, num_recommendations=12):
            return []

# Configuración para encontrar las plantillas con T mayúscula
app = Flask(__name__, template_folder='../Templates')

# Variables globales para almacenar datos en caché
_perfumes = None
_seasonal = None
_notes = None
_gender = None
recommender = None

# Cargar los datos
def load_data():
    global _perfumes, _seasonal, _notes, _gender
    
    # Si los datos ya están cargados, devolverlos sin volver a procesar
    if _perfumes is not None:
        print("Usando datos en caché...")
        return _perfumes, _seasonal, _notes, _gender
    
    print("Cargando datos por primera vez...")
    
    # Inicializar con valores vacíos
    perfumes = []
    seasonal = {}
    notes = {}
    gender = {}
    
    # Intentar diferentes rutas posibles para la base de datos
    database_paths = [
        os.path.join(project_root, 'data', 'fra_cleaned_images.csv'),
        os.path.join(project_root, 'fra_cleaned_images.csv'),
        os.path.join(current_dir, '..', 'data', 'fra_cleaned_images.csv'),
        os.path.join(current_dir, 'data', 'fra_cleaned_images.csv')
    ]
    
    df = None
    for path in database_paths:
        print(f"Intentando cargar desde: {path}")
        if os.path.exists(path):
            try:
                # Intentar cargar el CSV con distintas codificaciones
                try:
                    df = pd.read_csv(path, sep=';', encoding='utf-8')
                    print(f"¡Éxito! Cargado con UTF-8: {path}")
                    break
                except UnicodeDecodeError:
                    df = pd.read_csv(path, sep=';', encoding='latin1')
                    print(f"¡Éxito! Cargado con LATIN1: {path}")
                    break
            except Exception as e:
                print(f"Error al cargar {path}: {e}")
    
    if df is None:
        print("No se pudo cargar la base de datos de ninguna ruta")
    else:
        # Convertir a lista de diccionarios
        perfumes = df.to_dict('records')
        print(f"Cargados {len(perfumes)} perfumes")
        
        # Mostrar ejemplo de un perfume para depuración
        if perfumes:
            print("Ejemplo de un perfume:")
            sample_perfume = perfumes[0]
            for key, value in sample_perfume.items():
                print(f"  {key}: {value}")
        
        # Procesar datos para facilitar su uso
        for perfume in perfumes:
            # Asegurar que todos los campos existan
            for field in ['Perfume', 'Brand', 'Gender', 'Top', 'Middle', 'Base', 'mainaccord1', 'mainaccord2', 'mainaccord3']:
                if field not in perfume or pd.isna(perfume[field]):
                    perfume[field] = ""
            
            # Crear campo 'name' para compatibilidad con el código existente
            perfume['name'] = f"{perfume['Brand']} {perfume['Perfume']}".strip()
            
            # Crear campo 'notes' para compatibilidad
            notes_list = []
            
            # Procesar Top, Middle y Base
            for section in ['Top', 'Middle', 'Base']:
                if perfume[section] and isinstance(perfume[section], str):
                    section_notes = [note.strip() for note in perfume[section].split(',') if note.strip()]
                    notes_list.extend(section_notes)
            
            # Añadir mainaccords si no están ya en las notas
            for i in range(1, 6):
                accord_key = f'mainaccord{i}'
                if accord_key in perfume and perfume[accord_key] and not pd.isna(perfume[accord_key]):
                    # Convertir a cadena si es un número
                    if isinstance(perfume[accord_key], (int, float)):
                        accord_value = str(perfume[accord_key])
                    else:
                        accord_value = str(perfume[accord_key])
                    
                    if accord_value not in notes_list:
                        notes_list.append(accord_value)
            
            # Unir todas las notas en una cadena
            perfume['notes'] = ', '.join(notes_list) if notes_list else ""
            
            # Asegurar que el ID sea entero si es posible
            if 'perfume_id' in perfume and perfume['perfume_id']:
                try:
                    perfume['id'] = int(perfume['perfume_id'])
                except (ValueError, TypeError):
                    perfume['id'] = 0

    # Generar notas y recomendaciones
    if perfumes:
        # Extraer notas para crear datos de frecuencia
        all_notes = {}
        for perfume in perfumes:
            if 'notes' in perfume and perfume['notes']:
                for note in [n.strip() for n in perfume['notes'].split(',')]:
                    if note:
                        all_notes[note] = all_notes.get(note, 0) + 1
        
        # Ordenar por frecuencia
        sorted_notes = {k: v for k, v in sorted(all_notes.items(), key=lambda item: item[1], reverse=True)}
        notes = {'top_notes': sorted_notes}
        
        # Crear datos de temporadas basados en notas
        seasons = {'spring': [], 'summer': [], 'fall': [], 'winter': []}
        
        # Notas características por temporada
        spring_notes = ['floral', 'green', 'citrus', 'fresh', 'light']
        summer_notes = ['citrus', 'fresh', 'aquatic', 'fruity', 'light']
        fall_notes = ['woody', 'spicy', 'amber', 'warm', 'oriental']
        winter_notes = ['woody', 'warm spicy', 'amber', 'vanilla', 'balsamic']
        
        for perfume in perfumes:
            # Calcular puntuación por temporada basada en notas
            perfume['spring'] = 0
            perfume['summer'] = 0
            perfume['fall'] = 0
            perfume['winter'] = 0
            
            # Revisar mainaccords
            for i in range(1, 6):
                accord_key = f'mainaccord{i}'
                if accord_key in perfume and perfume[accord_key]:
                    accord = str(perfume[accord_key]).lower()
                    
                    # Spring score
                    if any(note in accord for note in spring_notes):
                        perfume['spring'] += (6-i) * 10  # Las primeras notas puntúan más
                    
                    # Summer score
                    if any(note in accord for note in summer_notes):
                        perfume['summer'] += (6-i) * 10
                    
                    # Fall score
                    if any(note in accord for note in fall_notes):
                        perfume['fall'] += (6-i) * 10
                    
                    # Winter score
                    if any(note in accord for note in winter_notes):
                        perfume['winter'] += (6-i) * 10
            
            # Asignar a las temporadas con puntuación mínima
            min_score = 20
            if perfume['spring'] >= min_score:
                seasons['spring'].append(perfume)
            if perfume['summer'] >= min_score:
                seasons['summer'].append(perfume)
            if perfume['fall'] >= min_score:
                seasons['fall'].append(perfume)
            if perfume['winter'] >= min_score:
                seasons['winter'].append(perfume)
        
        # Ordenar por puntuación
        for season in seasons:
            seasons[season] = sorted(seasons[season], key=lambda x: x.get(season, 0), reverse=True)[:20]  # Top 20
            
        seasonal = seasons
        
        # Generar datos de género
        gender_categories = {'male': [], 'female': [], 'unisex': []}
        
        for perfume in perfumes:
            gender_value = perfume.get('Gender', '').lower()
            
            if 'men' in gender_value and 'women' not in gender_value:
                gender_categories['male'].append(perfume)
            elif 'women' in gender_value and 'men' not in gender_value:
                gender_categories['female'].append(perfume)
            elif 'unisex' in gender_value or ('men' in gender_value and 'women' in gender_value):
                gender_categories['unisex'].append(perfume)
        
        # Ordenar por rating si está disponible
        for category in gender_categories:
            try:
                gender_categories[category] = sorted(
                    gender_categories[category], 
                    key=lambda x: float(str(x.get('Rating Value', '0')).replace(',', '.')), 
                    reverse=True
                )[:20]  # Top 20
            except:
                # Si hay error en la ordenación, dejar como está
                gender_categories[category] = gender_categories[category][:20]
                
        gender = gender_categories
    
    # Guardar en variables globales para caché
    _perfumes = perfumes
    _seasonal = seasonal
    _notes = notes
    _gender = gender
    
    return perfumes, seasonal, notes, gender

def get_perfume_image_url(perfume):
    """
    Obtiene la URL de la imagen del perfume.
    """
    # 1. Probar a generar la URL a partir del perfume_id
    if 'perfume_id' in perfume and perfume['perfume_id'] and not pd.isna(perfume['perfume_id']):
        perfume_id = str(perfume['perfume_id']).strip()
        if perfume_id.isdigit():
            fragrantica_url = f"https://fimgs.net/mdimg/perfume/375x500.{perfume_id}.jpg"
            return fragrantica_url
    
    # 2. Probar con image_url si existe y es válida
    if 'image_url' in perfume and perfume['image_url'] and not pd.isna(perfume['image_url']):
        image_url = str(perfume['image_url'])
        return image_url
    
    # 3. Generar el placeholder como último recurso
    # Extraer nombre y marca
    name = ""
    brand = ""
    
    if 'name' in perfume and perfume['name']:
        name = str(perfume['name']).strip()
    elif 'Perfume' in perfume and perfume['Perfume']:
        name = str(perfume['Perfume']).strip()
    
    if 'Brand' in perfume and perfume['Brand']:
        brand = str(perfume['Brand']).strip()
    
    # Determinar el género para colores
    gender = ""
    if 'Gender' in perfume:
        gender = str(perfume['Gender']).lower() if perfume['Gender'] else ""
    
    # Colores basados en género
    bg_color = "87CEEB"  # Azul claro por defecto
    text_color = "000000"  # Negro
    
    if "men" in gender and "women" not in gender:
        bg_color = "4682B4"  # Azul acero
    elif "women" in gender and "men" not in gender:
        bg_color = "FF69B4"  # Rosa
    elif "unisex" in gender or ("men" in gender and "women" in gender):
        bg_color = "9370DB"  # Púrpura medio
    
    # Crear texto para la imagen placeholder
    display_text = ""
    if brand and name:
        if brand in name:
            display_text = name
        else:
            display_text = f"{brand} {name}"
    elif name:
        display_text = name
    elif brand:
        display_text = brand
    else:
        display_text = "Perfume"
    
    # Limitar longitud
    if len(display_text) > 30:
        display_text = display_text[:27] + "..."
    
    # Escapar caracteres especiales
    import urllib.parse
    display_text = urllib.parse.quote_plus(display_text)
    
    # Generar URL de placeholder
    placeholder_url = f"https://via.placeholder.com/300x400/{bg_color}/{text_color}?text={display_text}"
    
    return placeholder_url

# Rutas
@app.route('/')
def home():
    perfumes, seasonal, notes, gender = load_data()
    
    # Obtener las temporadas disponibles
    seasons = list(seasonal.keys()) if seasonal else []
    
    # Obtener las notas más comunes
    top_notes = list(notes.get('top_notes', {}).keys())[:10] if notes else []
    
    return render_template('index.html', 
                          perfumes_count=len(perfumes),
                          seasons=seasons,
                          top_notes=top_notes)

@app.route('/season/<season>')
def season_perfumes(season):
    perfumes, seasonal, notes, gender = load_data()
    
    if seasonal and season in seasonal:
        recommendations = seasonal[season]
        
        # Asegurarse de que todos los perfumes tienen un valor para la temporada
        for perfume in recommendations:
            if season not in perfume or not perfume[season]:
                perfume[season] = 0
        
        # Ordenar por valoración de temporada (de mayor a menor)
        recommendations = sorted(
            recommendations, 
            key=lambda x: float(x.get(season, 0)) if isinstance(x.get(season), (int, float, str)) and str(x.get(season)).replace('.', '', 1).isdigit() else 0, 
            reverse=True
        )
        
        # Pasar la función de imagen a la plantilla
        return render_template('season.html', 
                              season=season,
                              perfumes=recommendations,
                              get_perfume_image_url=get_perfume_image_url)
    else:
        # Si no hay datos para esta temporada, mostrar mensaje
        return render_template('error.html', 
                              message=f"No se encontraron datos para la temporada {season}",
                              suggestion="Prueba con otra temporada o regresa al inicio")

@app.route('/notes')
def notes_page():
    perfumes, seasonal, notes_data, gender = load_data()
    
    return render_template('notes.html', 
                          notes=notes_data.get('top_notes', {}))

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    perfumes, seasonal, notes, gender = load_data()
    
    results = []
    for perfume in perfumes:
        name_match = False
        brand_match = False
        
        # Verificar coincidencia en nombre
        if 'Perfume' in perfume and isinstance(perfume['Perfume'], str):
            name_match = query in perfume['Perfume'].lower()
        elif 'name' in perfume and isinstance(perfume['name'], str):
            name_match = query in perfume['name'].lower()
        
        # Verificar coincidencia en marca
        if 'Brand' in perfume and isinstance(perfume['Brand'], str):
            brand_match = query in perfume['Brand'].lower()
        
        if name_match or brand_match:
            results.append(perfume)
    
    return render_template('search_results.html',
                          query=query,
                          results=results[:20],  # Limitar a 20 resultados
                          get_perfume_image_url=get_perfume_image_url)

@app.route('/api/perfumes')
def api_perfumes():
    perfumes, seasonal, notes, gender = load_data()
    return jsonify(perfumes[:50])  # Limitar a 50 para no sobrecargar

@app.route('/api/recommendations/season/<season>')
def api_season(season):
    perfumes, seasonal, notes, gender = load_data()
    
    if seasonal and season in seasonal:
        return jsonify(seasonal[season])
    else:
        return jsonify({"error": "Season not found"}), 404

@app.route('/perfume/<int:perfume_id>')
def perfume_detail(perfume_id):
    """Vista detallada de un perfume específico"""
    perfumes, seasonal, notes, gender = load_data()
    
    # Buscar el perfume por ID
    perfume = None
    for p in perfumes:
        if 'id' in p and str(p['id']) == str(perfume_id):
            perfume = p
            break
        elif 'perfume_id' in p and str(p['perfume_id']) == str(perfume_id):
            perfume = p
            break
    
    # Si no se encuentra por ID, intentar buscar por índice en el array
    if perfume is None and 0 <= perfume_id < len(perfumes):
        perfume = perfumes[perfume_id]
    
    if perfume:
        # Obtener URL de imagen para el perfume
        image_url = get_perfume_image_url(perfume)
        
        # Encontrar perfumes similares (por marca o notas)
        similar_perfumes = []
        
        # Por marca
        if 'Brand' in perfume and perfume['Brand']:
            brand = perfume['Brand']
            for p in perfumes:
                if p != perfume and 'Brand' in p and p['Brand'] == brand:
                    similar_perfumes.append(p)
                    if len(similar_perfumes) >= 3:
                        break
        
        # Por notas si hay menos de 3 por marca
        if len(similar_perfumes) < 3:
            # Extraer notas del perfume actual
            perfume_notes = set()
            
            # Intentar extraer de mainaccords
            for i in range(1, 6):
                accord_key = f'mainaccord{i}'
                if accord_key in perfume and perfume[accord_key]:
                    perfume_notes.add(str(perfume[accord_key]).lower())
            
            # Buscar perfumes con notas similares
            if perfume_notes:
                for p in perfumes:
                    if p != perfume and p not in similar_perfumes:
                        p_notes = set()
                        for i in range(1, 6):
                            accord_key = f'mainaccord{i}'
                            if accord_key in p and p[accord_key]:
                                p_notes.add(str(p[accord_key]).lower())
                        
                        # Si hay al menos una nota en común
                        common_notes = perfume_notes & p_notes
                        if common_notes:
                            similar_perfumes.append(p)
                            if len(similar_perfumes) >= 5:  # Limitar a 5 perfumes similares
                                break
        
        # Obtener información de temporadas si está disponible
        seasons_data = {}
        for season in ['spring', 'summer', 'fall', 'winter']:
            if season in perfume and isinstance(perfume[season], (int, float)):
                seasons_data[season] = perfume[season]
        
        return render_template('perfume_detail.html', 
                               perfume=perfume,
                               similar_perfumes=similar_perfumes[:5],
                               seasons=seasons_data,
                               image_url=image_url,
                               get_perfume_image_url=get_perfume_image_url)
    else:
        return render_template('error.html', 
                              message=f"No se encontró el perfume con ID {perfume_id}",
                              suggestion="Prueba buscando por nombre o marca")

# NUEVA RUTA: Cuestionario de preferencias
@app.route('/preferences')
def preferences():
    """Muestra el cuestionario de preferencias para la recomendación personalizada"""
    perfumes, seasonal, notes, gender = load_data()
    
    # Obtener las notas más populares para el cuestionario
    top_notes = list(notes.get('top_notes', {}).keys())[:15] if notes else [
        'Vainilla', 'Bergamota', 'Rosa', 'Jazmín', 'Ámbar', 
        'Pachulí', 'Sándalo', 'Cedro', 'Lavanda', 'Neroli',
        'Cítricos', 'Almizcle', 'Vetiver', 'Canela', 'Cuero'
    ]
    
    return render_template('preferences.html',
                          top_notes=top_notes,
                          perfumes_count=len(perfumes))

# NUEVA RUTA: Procesar formulario y mostrar recomendaciones
@app.route('/recommend', methods=['POST'])
def recommend_perfumes():
    """Procesa el formulario y genera recomendaciones personalizadas"""
    global recommender
    
    # Cargar datos
    perfumes, seasonal, notes, gender = load_data()
    
    # Inicializar el recomendador si no existe
    if recommender is None:
        recommender = PerfumeRecommender().load_data(perfumes)
    
    # Obtener datos del formulario
    user_preferences = {
        'gender_preference': request.form.get('gender_preference', 'unisex'),
        'season': request.form.get('season', 'spring'),
        'budget': request.form.get('budget', 'medium')
    }
    
    # Procesar notas preferidas (pueden ser múltiples)
    preferred_notes = request.form.getlist('preferred_notes')
    if preferred_notes:
        user_preferences['preferred_notes'] = preferred_notes
    
    # Obtener recomendaciones
    recommendations = recommender.get_recommendations(
        user_preferences, 
        num_recommendations=12
    )
    
    # Obtener URLs de imágenes para las recomendaciones
    for rec in recommendations:
        rec['image_url'] = get_perfume_image_url(rec)
    
    # Renderizar plantilla de resultados
    return render_template('recommendations.html',
                          preferences=user_preferences,
                          recommendations=recommendations,
                          get_perfume_image_url=get_perfume_image_url)

if __name__ == '__main__':
    app.run(debug=True)