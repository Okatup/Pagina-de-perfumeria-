# app.py
from flask import Flask, render_template, request, jsonify
import json
import os
import random
import pandas as pd
import sys
import pandas as pd
from unidecode import unidecode
from flask import Flask, request, render_template
from scripts.utils import normalize, format_text



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

df = pd.read_csv('data/fra_perfumes_con_imagenes.csv')
def norm(x):
    return unidecode(str(x)).lower()


def get_top_rated_perfumes(perfumes, min_ratings=10, limit=8):
    """
    Obtiene los perfumes mejor valorados con un mínimo de valoraciones
    
    Args:
        perfumes: Lista de perfumes
        min_ratings: Número mínimo de valoraciones para considerar un perfume
        limit: Número máximo de perfumes a devolver
    
    Returns:
        Lista de perfumes mejor valorados
    """
    # Filtrar perfumes con al menos min_ratings valoraciones
    qualified_perfumes = []
    
    for perfume in perfumes:
        # Verificar si tiene Rating Value y Rating Count
        if 'Rating Value' in perfume and 'Rating Count' in perfume:
            try:
                # Convertir Rating Value a float
                rating_str = str(perfume['Rating Value']).replace(',', '.')
                rating = float(rating_str)
                
                # Convertir Rating Count a int
                if isinstance(perfume['Rating Count'], (int, float)):
                    count = int(perfume['Rating Count'])
                else:
                    count_str = str(perfume['Rating Count']).strip()
                    count = int(count_str) if count_str.isdigit() else 0
                
                # Filtrar por número mínimo de valoraciones
                if count >= min_ratings:
                    # Añadir a la lista con rating y count
                    perfume_copy = perfume.copy()
                    perfume_copy['rating_float'] = rating
                    perfume_copy['rating_count_int'] = count
                    qualified_perfumes.append(perfume_copy)
            except (ValueError, TypeError):
                # Ignorar si hay error al convertir
                continue
    
    # Ordenar por valoración (de mayor a menor)
    sorted_perfumes = sorted(qualified_perfumes, key=lambda x: x['rating_float'], reverse=True)
    
    # Devolver los mejores hasta el límite
    return sorted_perfumes[:limit]

# Formatear el nombre del perfume
def format_perfume_name(name):
    if not isinstance(name, str):
        return ""
    return name.replace('-', ' ').title()


# Rutas
@app.route('/')
def home():
    perfumes, seasonal, notes, gender = load_data()
    
    # Obtener las temporadas disponibles
    seasons = list(seasonal.keys()) if seasonal else []
    
    # Obtener las notas más comunes
    top_notes = list(notes.get('top_notes', {}).keys())[:10] if notes else []

    # Obtener los perfumes mejor valorados (mínimo 50 valoraciones)
    top_rated = get_top_rated_perfumes(perfumes, min_ratings=50, limit=8)
    
    return render_template('index.html', 
                          perfumes_count=len(perfumes),
                          seasons=seasons,
                          top_notes=top_notes,
                          top_rated=top_rated,
                          get_perfume_image_url=get_perfume_image_url)

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
    # Obtener parámetros de búsqueda y filtros
    query = request.args.get('q', '').lower().strip()
    page = int(request.args.get('page', 1))
    per_page = 24  # Número de resultados por página
    
    # Parámetros de filtro
    gender_filters = request.args.getlist('gender')
    min_rating = request.args.get('min_rating', '')
    min_votes = request.args.get('min_votes', '')
    year_from = request.args.get('year_from', '')
    year_to = request.args.get('year_to', '')
    note_filters = request.args.getlist('notes')
    sort_by = request.args.get('sort', 'relevance')
    
    # Guardar filtros seleccionados para la plantilla
    selected_filters = {
        'gender': gender_filters,
        'min_rating': min_rating,
        'min_votes': min_votes,
        'year_from': year_from,
        'year_to': year_to,
        'notes': note_filters
    }
    
    # Construir parámetros para enlaces de paginación
    filter_params = {}
    if gender_filters:
        filter_params['gender'] = gender_filters
    if min_rating:
        filter_params['min_rating'] = min_rating
    if min_votes:
        filter_params['min_votes'] = min_votes
    if year_from:
        filter_params['year_from'] = year_from
    if year_to:
        filter_params['year_to'] = year_to
    if note_filters:
        filter_params['notes'] = note_filters
    if sort_by != 'relevance':
        filter_params['sort'] = sort_by
    
    if not query:
        return render_template('search_results.html',
                               query="",
                               results=[],
                               current_page=1,
                               total_pages=1,
                               total_results=0,
                               selected_filters=selected_filters,
                               filter_params=filter_params,
                               sort_by=sort_by,
                               popular_notes=get_popular_notes(10),
                               get_perfume_image_url=get_perfume_image_url)
    
    perfumes, seasonal, notes, gender = load_data()
    
    # Obtener las notas más populares para los filtros
    popular_notes_list = get_popular_notes(15)
    
    results = []
    for perfume in perfumes:
        # Inicializamos un puntaje de coincidencia que nos ayudará a ordenar los resultados
        match_score = 0
        match_found = False
        
        # Búsqueda en campos principales
        name_match = False
        brand_match = False
        
        # Verificar coincidencia en nombre del perfume
        if 'Perfume' in perfume and isinstance(perfume['Perfume'], str):
            perfume_name = perfume['Perfume'].lower()
            if query in perfume_name:
                name_match = True
                match_score += 10  # Prioridad alta si coincide con el nombre
                if query == perfume_name:
                    match_score += 20  # Coincidencia exacta
        
        # Verificar coincidencia en nombre completo
        if 'name' in perfume and isinstance(perfume['name'], str):
            if query in perfume['name'].lower():
                name_match = True
                match_score += 8
        
        # Verificar coincidencia en marca
        if 'Brand' in perfume and isinstance(perfume['Brand'], str):
            brand = perfume['Brand'].lower()
            if query in brand:
                brand_match = True
                match_score += 5
                if query == brand:
                    match_score += 15  # Coincidencia exacta con la marca
        
        # Búsqueda en campos adicionales
        # Verificar coincidencia en notas (mainaccords)
        for i in range(1, 6):
            accord_key = f'mainaccord{i}'
            if accord_key in perfume and perfume[accord_key] and isinstance(perfume[accord_key], str):
                if query in perfume[accord_key].lower():
                    match_found = True
                    match_score += 3
        
        # Verificar coincidencia en Top, Middle, Base
        for section in ['Top', 'Middle', 'Base']:
            if section in perfume and perfume[section] and isinstance(perfume[section], str):
                if query in perfume[section].lower():
                    match_found = True
                    match_score += 2
        
        # Verificar coincidencia en perfumista
        for perfumer_key in ['Perfumer1', 'Perfumer2']:
            if perfumer_key in perfume and perfume[perfumer_key] and isinstance(perfume[perfumer_key], str):
                if query in perfume[perfumer_key].lower():
                    match_found = True
                    match_score += 4
        
        # Si hay coincidencia en cualquier campo, verificar filtros adicionales
        if name_match or brand_match or match_found:
            # Aplicar filtros
            meets_filters = True
            
            # Filtro de género
            if gender_filters:
                gender_match = False
                if 'Gender' in perfume and perfume['Gender']:
                    gender_value = perfume['Gender'].lower()
                    for gender_filter in gender_filters:
                        if gender_value == gender_filter.lower():
                            gender_match = True
                            break
                if not gender_match:
                    meets_filters = False
            
            # Filtro de valoración mínima
            if min_rating and meets_filters:
                if 'Rating Value' in perfume and perfume['Rating Value']:
                    try:
                        rating_value = float(str(perfume['Rating Value']).replace(',', '.'))
                        if rating_value < float(min_rating):
                            meets_filters = False
                    except (ValueError, TypeError):
                        meets_filters = False
                else:
                    meets_filters = False
            
            # Filtro de votos mínimos
            if min_votes and meets_filters:
                if 'Rating Count' in perfume and perfume['Rating Count']:
                    try:
                        if isinstance(perfume['Rating Count'], (int, float)):
                            votes_count = int(perfume['Rating Count'])
                        else:
                            votes_count = int(perfume['Rating Count'])
                        if votes_count < int(min_votes):
                            meets_filters = False
                    except (ValueError, TypeError):
                        meets_filters = False
                else:
                    meets_filters = False
            
            # Filtro de año desde
            if year_from and meets_filters:
                if 'Year' in perfume and perfume['Year']:
                    try:
                        if isinstance(perfume['Year'], (int, float)):
                            year_value = int(perfume['Year'])
                        else:
                            year_value = int(float(str(perfume['Year']).replace(',', '.')))
                        if year_value < int(year_from):
                            meets_filters = False
                    except (ValueError, TypeError):
                        meets_filters = False
                else:
                    meets_filters = False
            
            # Filtro de año hasta
            if year_to and meets_filters:
                if 'Year' in perfume and perfume['Year']:
                    try:
                        if isinstance(perfume['Year'], (int, float)):
                            year_value = int(perfume['Year'])
                        else:
                            year_value = int(float(str(perfume['Year']).replace(',', '.')))
                        if year_value > int(year_to):
                            meets_filters = False
                    except (ValueError, TypeError):
                        meets_filters = False
                else:
                    meets_filters = False
            
            # Filtro de notas
            if note_filters and meets_filters:
                has_note = False
                # Buscar en mainaccords
                for i in range(1, 6):
                    accord_key = f'mainaccord{i}'
                    if accord_key in perfume and perfume[accord_key]:
                        for note in note_filters:
                            if note.lower() in str(perfume[accord_key]).lower():
                                has_note = True
                                break
                        if has_note:
                            break

                        if not has_note:
                             meets_filters = False
            
            # Si cumple con todos los filtros, añadir a resultados
            if meets_filters:
                perfume_copy = perfume.copy()
                
                # Preparar valores para ordenamiento
                try:
                    if 'Rating Value' in perfume:
                        perfume_copy['rating_float'] = float(str(perfume['Rating Value']).replace(',', '.'))
                    else:
                        perfume_copy['rating_float'] = 0
                        
                    if 'Rating Count' in perfume:
                        if isinstance(perfume['Rating Count'], (int, float)):
                            perfume_copy['rating_count_int'] = int(perfume['Rating Count'])
                        else:
                            perfume_copy['rating_count_int'] = int(perfume['Rating Count'])
                    else:
                        perfume_copy['rating_count_int'] = 0
                        
                    if 'Year' in perfume and perfume['Year']:
                        if isinstance(perfume['Year'], (int, float)):
                            perfume_copy['year_int'] = int(perfume['Year'])
                        else:
                            perfume_copy['year_int'] = int(float(str(perfume['Year']).replace(',', '.')))
                    else:
                        perfume_copy['year_int'] = 0
                except (ValueError, TypeError):
                    # Asignar valores predeterminados si hay error
                    perfume_copy['rating_float'] = 0
                    perfume_copy['rating_count_int'] = 0
                    perfume_copy['year_int'] = 0
                
                perfume_copy['match_score'] = match_score
                # Formatear nombre del perfume
                raw_name = perfume_copy.get('name') or perfume_copy.get('Perfume') or ''
                perfume_copy['formatted_name'] = format_text(raw_name)
                raw_brand = perfume_copy.get('Brand') or ''
                perfume_copy['formatted_brand'] = format_text(raw_brand)
                results.append(perfume_copy)
    
    # Ordenar resultados según el criterio seleccionado
    if sort_by == 'rating':
        results = sorted(results, key=lambda x: x['rating_float'], reverse=True)
    elif sort_by == 'votes':
        results = sorted(results, key=lambda x: x['rating_count_int'], reverse=True)
    elif sort_by == 'year':
        results = sorted(results, key=lambda x: x['year_int'], reverse=True)
    elif sort_by == 'year_asc':
        results = sorted(results, key=lambda x: x['year_int'])
    else:  # default: relevance
        results = sorted(results, key=lambda x: x['match_score'], reverse=True)
    
    # Calcular paginación
    total_results = len(results)
    total_pages = (total_results + per_page - 1) // per_page  # Redondeo hacia arriba
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_results)
    current_page_results = results[start_idx:end_idx]

    # Clonamos los filtros para usarlos en los enlaces de paginación
    pagination_params = filter_params.copy()

    # Aseguramos que el criterio de ordenamiento también se mantenga
    pagination_params['sort'] = sort_by
    
    return render_template('search_results.html',
                          query=query,
                          results=current_page_results,
                          total_results=total_results,
                          current_page=page,
                          total_pages=total_pages,
                          selected_filters=selected_filters,
                          filter_params=filter_params,
                          pagination_params=pagination_params,
                          sort_by=sort_by,
                          popular_notes=popular_notes_list,
                          get_perfume_image_url=get_perfume_image_url)

# Función para obtener las notas más populares
def get_popular_notes(limit=15):
    """Obtiene las notas más populares para los filtros"""
    popular_notes = [
        'woody', 'amber', 'vanilla', 'citrus', 'musky',
        'floral', 'sweet', 'powdery', 'fresh', 'spicy',
        'fruity', 'aromatic', 'bergamot', 'rose', 'jasmine',
        'sandalwood', 'oud', 'leather', 'lavender', 'patchouli'
    ]
    
    return popular_notes[:limit] 


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

        # Formatear nombre del perfume
        # Formatear nombre y marca principal
        raw_name = perfume.get('name') or perfume.get('Perfume') or ''
        perfume['formatted_name'] = format_text(raw_name)
        perfume['formatted_brand'] = format_text(perfume.get('Brand', ''))
        
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
        
        for sp in similar_perfumes:
            raw_name = sp.get('name') or sp.get('Perfume') or ''
            sp['formatted_name'] = format_text(raw_name)
            sp['formatted_brand'] = format_text(sp.get('Brand', ''))

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