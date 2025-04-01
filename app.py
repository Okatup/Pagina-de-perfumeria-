# app.py
from flask import Flask, render_template, request, jsonify
import json
import os
import random

app = Flask(__name__)

# Cargar los datos
def load_data():
    # Inicializar con valores vacíos
    perfumes = []
    seasonal = {}
    notes = {}
    gender = {}
    
    # Cargar perfumes_database.json (obligatorio)
    try:
        with open('perfumes_database.json', 'r', encoding='utf-8') as f:
            perfumes = json.load(f)
        print(f"Cargados {len(perfumes)} perfumes de la base de datos")
    except FileNotFoundError:
        print("Advertencia: No se encontró perfumes_database.json")
        # Intentar con fra_cleaned.csv o fra_perfumes.csv convertido a JSON
        try:
            import pandas as pd
            if os.path.exists('fra_cleaned.csv'):
                df = pd.read_csv('fra_cleaned.csv')
                perfumes = df.to_dict('records')
                print(f"Cargados {len(perfumes)} perfumes desde fra_cleaned.csv")
            elif os.path.exists('fra_perfumes.csv'):
                df = pd.read_csv('fra_perfumes.csv')
                perfumes = df.to_dict('records')
                print(f"Cargados {len(perfumes)} perfumes desde fra_perfumes.csv")
        except:
            print("No se pudo cargar ninguna fuente de datos de perfumes")
    
    # Cargar archivos opcionales
    try:
        with open('seasonal_recommendations.json', 'r', encoding='utf-8') as f:
            seasonal = json.load(f)
        print("Archivo seasonal_recommendations.json cargado correctamente")
    except FileNotFoundError:
        print("Advertencia: No se encontró seasonal_recommendations.json, se usarán datos simulados")
        # Crear datos simulados de temporadas
        if perfumes:
            # Identificar columnas de temporadas si existen
            season_cols = []
            sample_perfume = perfumes[0]
            for key in sample_perfume.keys():
                if key.lower() in ['spring', 'summer', 'fall', 'winter', 'primavera', 'verano', 'otoño', 'invierno']:
                    season_cols.append(key)
            
            # Si hay columnas de temporadas, usarlas para crear recomendaciones
            if season_cols:
                for season in season_cols:
                    # Ordenar por valor de temporada (descendente)
                    top_perfumes = sorted(perfumes, key=lambda x: float(x.get(season, 0)) if isinstance(x.get(season), (int, float, str)) and str(x.get(season)).replace('.', '', 1).isdigit() else 0, reverse=True)
                    seasonal[season] = top_perfumes[:10]  # Tomar los 10 mejores
            else:
                # Si no hay datos de temporadas, crear datos aleatorios
                seasons = ['spring', 'summer', 'fall', 'winter']
                for season in seasons:
                    random_perfumes = random.sample(perfumes, min(10, len(perfumes)))
                    for p in random_perfumes:
                        p[season] = random.randint(60, 95)  # Asignar puntuación aleatoria
                    seasonal[season] = random_perfumes
    
    try:
        with open('notes_data.json', 'r', encoding='utf-8') as f:
            notes = json.load(f)
        print("Archivo notes_data.json cargado correctamente")
    except FileNotFoundError:
        print("Advertencia: No se encontró notes_data.json, se usarán datos simulados")
        # Crear datos simulados de notas
        common_notes = {
            'Vainilla': 120, 
            'Bergamota': 100, 
            'Rosa': 95, 
            'Jazmín': 90, 
            'Ámbar': 85, 
            'Pachulí': 80, 
            'Sándalo': 75, 
            'Cedro': 70, 
            'Lavanda': 65, 
            'Neroli': 60
        }
        notes = {'top_notes': common_notes}
    
    try:
        with open('gender_recommendations.json', 'r', encoding='utf-8') as f:
            gender = json.load(f)
        print("Archivo gender_recommendations.json cargado correctamente")
    except FileNotFoundError:
        print("Advertencia: No se encontró gender_recommendations.json")
    
    return perfumes, seasonal, notes, gender

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
        return render_template('season.html', 
                              season=season,
                              perfumes=recommendations)
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
        if 'name' in perfume and isinstance(perfume['name'], str):
            name_match = query in perfume['name'].lower()
        elif 'title' in perfume and isinstance(perfume['title'], str):
            name_match = query in perfume['title'].lower()
        
        # Verificar coincidencia en marca
        if 'brand' in perfume and isinstance(perfume['brand'], str):
            brand_match = query in perfume['brand'].lower()
        
        if name_match or brand_match:
            results.append(perfume)
    
    return render_template('search_results.html',
                          query=query,
                          results=results[:20])  # Limitar a 20 resultados

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




#Ruta para obtener recomendaciones de género
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
    
    # Si no se encuentra por ID, intentar buscar por índice en el array
    if perfume is None and 0 <= perfume_id < len(perfumes):
        perfume = perfumes[perfume_id]
    
    if perfume:
        # Encontrar perfumes similares (por marca o notas)
        similar_perfumes = []
        
        # Por marca
        if 'brand' in perfume and perfume['brand']:
            for p in perfumes:
                if p != perfume and 'brand' in p and p['brand'] == perfume['brand']:
                    similar_perfumes.append(p)
                    if len(similar_perfumes) >= 3:
                        break
        
        # Por notas si hay menos de 3 por marca
        if len(similar_perfumes) < 3 and 'notes' in perfume and perfume['notes']:
            perfume_notes = set()
            
            # Extraer notas del perfume actual
            try:
                if isinstance(perfume['notes'], str):
                    import json
                    notes_dict = json.loads(perfume['notes'])
                    perfume_notes = set(notes_dict.keys())
                elif isinstance(perfume['notes'], dict):
                    perfume_notes = set(perfume['notes'].keys())
            except:
                # Si no se pueden analizar las notas, intentar como texto simple
                if isinstance(perfume['notes'], str):
                    for separator in [',', ';', '|']:
                        if separator in perfume['notes']:
                            perfume_notes = set(n.strip() for n in perfume['notes'].split(separator))
                            break
            
            # Buscar perfumes con notas similares
            if perfume_notes:
                for p in perfumes:
                    if p != perfume and 'notes' in p:
                        p_notes = set()
                        
                        try:
                            if isinstance(p['notes'], str):
                                try:
                                    notes_dict = json.loads(p['notes'])
                                    p_notes = set(notes_dict.keys())
                                except:
                                    for separator in [',', ';', '|']:
                                        if separator in p['notes']:
                                            p_notes = set(n.strip() for n in p['notes'].split(separator))
                                            break
                            elif isinstance(p['notes'], dict):
                                p_notes = set(p['notes'].keys())
                        except:
                            continue
                        
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
                               seasons=seasons_data)
    else:
        return render_template('error.html', 
                              message=f"No se encontró el perfume con ID {perfume_id}",
                              suggestion="Prueba buscando por nombre o marca")


if __name__ == '__main__':
    app.run(debug=True)
