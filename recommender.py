import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import json
import os

class PerfumeRecommender:
    """
    Sistema de recomendación de perfumes basado en preferencias del usuario
    """
    
    def __init__(self):
        self.perfumes_data = None
        self.notes_data = None
        
    def load_data(self, perfumes_data):
        """
        Carga los datos de perfumes para el sistema de recomendación
        """
        self.perfumes_data = perfumes_data
        
        # Extraer y normalizar información de notas
        self.preprocess_notes()
        
        # Procesar datos de temporadas
        self.preprocess_seasonal_data()
        
        print(f"Recomendador inicializado con {len(self.perfumes_data)} perfumes")
        return self
    
    def preprocess_notes(self):
        """
        Preprocesa la información de notas para facilitar la búsqueda
        """
        if self.perfumes_data is None or len(self.perfumes_data) == 0:
            return
            
        # Convertir notas a formato estándar
        self.perfumes_data = pd.DataFrame(self.perfumes_data) if isinstance(self.perfumes_data, list) else self.perfumes_data
        
        if 'notes' in self.perfumes_data.columns:
            # Añadir columna de notas procesadas
            self.perfumes_data['processed_notes'] = self.perfumes_data['notes'].apply(self._extract_notes)
    
    def _extract_notes(self, notes_data):
        """Extrae notas de diferentes formatos posibles"""
        if pd.isna(notes_data) or notes_data is None:
            return []
            
        if isinstance(notes_data, str):
            # Intentar parsear como JSON
            try:
                notes_dict = json.loads(notes_data)
                if isinstance(notes_dict, dict):
                    return list(notes_dict.keys())
            except:
                # Intentar separar por comas, punto y coma o barras
                for separator in [',', ';', '|']:
                    if separator in notes_data:
                        return [note.strip() for note in notes_data.split(separator) if note.strip()]
                
                # Si no hay separadores, devolver como una sola nota
                return [notes_data.strip()]
                
        elif isinstance(notes_data, dict):
            return list(notes_data.keys())
            
        return []
    
    def preprocess_seasonal_data(self):
        """
        Preprocesa datos de temporadas para normalizar valores
        """
        if self.perfumes_data is None or not isinstance(self.perfumes_data, pd.DataFrame) or self.perfumes_data.empty:
            return
            
        # Temporadas a verificar
        seasons = ['spring', 'summer', 'fall', 'winter']
        
        # Identificar las temporadas presentes en los datos
        existing_seasons = [s for s in seasons if s in self.perfumes_data.columns]
        
        # Normalizar las puntuaciones de temporada
        for season in existing_seasons:
            # Convertir a valores numéricos
            self.perfumes_data[season] = pd.to_numeric(
                self.perfumes_data[season], errors='coerce').fillna(0)
    
    def get_recommendations(self, preferences, num_recommendations=10):
        """
        Genera recomendaciones basadas en las preferencias del usuario
        
        Args:
            preferences: Diccionario con preferencias del usuario
            num_recommendations: Número de recomendaciones a generar
            
        Returns:
            Lista de perfumes recomendados
        """
        if self.perfumes_data is None or not isinstance(self.perfumes_data, pd.DataFrame) or self.perfumes_data.empty:
            print("Error: No hay datos de perfumes cargados o formato incorrecto")
            return []
            
        # Trabajar con una copia del DataFrame
        df = self.perfumes_data.copy()
        
        # 1. Filtrar por género si se especifica
        if 'gender_preference' in preferences and preferences['gender_preference']:
            gender_pref = preferences['gender_preference']
            
            if gender_pref != 'unisex':
                # Normalizar la columna de género para la comparación
                if 'gender' in df.columns:
                    df['gender_norm'] = df['gender'].fillna('').astype(str).apply(
                        lambda x: 'male' if x.lower() in ['masculino', 'male', 'men', 'hombre'] 
                        else 'female' if x.lower() in ['femenino', 'female', 'women', 'mujer']
                        else 'unisex'
                    )
                    
                    # Si se prefiere un género específico, incluir ese género y unisex
                    df = df[df['gender_norm'].isin([gender_pref, 'unisex'])]
        
        # 2. Calcular puntuación para temporada
        if 'season' in preferences and preferences['season']:
            season = preferences['season']
            
            if season in df.columns:
                # Normalizar los valores de temporada
                max_value = df[season].max()
                if max_value > 0:
                    df['season_score'] = df[season] / max_value
                else:
                    df['season_score'] = 0
            else:
                df['season_score'] = 0
        else:
            df['season_score'] = 0
        
        # 3. Calcular puntuación para notas
        if 'preferred_notes' in preferences and preferences['preferred_notes']:
            # Convertir a lista si no lo es
            if isinstance(preferences['preferred_notes'], str):
                preferred_notes = [preferences['preferred_notes']]
            else:
                preferred_notes = preferences['preferred_notes']
                
            # Calcular puntuación de notas para cada perfume
            if 'processed_notes' in df.columns:
                def calculate_note_score(notes_list):
                    if notes_list is None or not isinstance(notes_list, list) or len(notes_list) == 0:
                        return 0
                    
                    # Contar coincidencias (caso insensitivo)
                    matches = 0
                    for note in notes_list:
                        if any(pref.lower() in note.lower() for pref in preferred_notes):
                            matches += 1
                    
                    # Normalizar por el total de notas preferidas
                    return matches / len(preferred_notes) if preferred_notes else 0
                
                df['note_score'] = df['processed_notes'].apply(calculate_note_score)
            else:
                df['note_score'] = 0
        else:
            df['note_score'] = 0
        
        # 4. Calcular puntuación para presupuesto
        if 'budget' in preferences and 'price' in df.columns:
            budget = preferences['budget']
            budget_ranges = {
                'low': (0, 50),
                'medium': (50, 100),
                'high': (100, 200),
                'luxury': (200, float('inf'))
            }
            
            if budget in budget_ranges:
                min_price, max_price = budget_ranges[budget]
                
                # Convertir precios a numérico
                df['price_numeric'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
                
                # Asignar puntuación por presupuesto
                def budget_score(price):
                    if min_price <= price <= max_price:
                        return 1.0  # Coincidencia exacta
                    elif price < min_price:
                        return 0.7  # Más barato de lo esperado
                    else:  # Más caro
                        ratio = max_price / price if price > 0 else 0
                        return max(0.3, ratio)  # Penalizar más a los muy caros
                        
                df['budget_score'] = df['price_numeric'].apply(budget_score)
            else:
                df['budget_score'] = 1.0
        else:
            df['budget_score'] = 1.0
        
        # 5. Calcular puntuación combinada
        # Pesos para diferentes factores
        weights = {
            'note_score': 0.5,     # Notas preferidas (factor más importante)
            'season_score': 0.3,   # Adecuación a la temporada
            'budget_score': 0.2    # Presupuesto
        }
        
        # Asegurarse de que todas las columnas de puntuación existan
        if 'note_score' not in df.columns:
            df['note_score'] = 0
        if 'season_score' not in df.columns:
            df['season_score'] = 0
        if 'budget_score' not in df.columns:
            df['budget_score'] = 1.0
            
        # Calcular puntuación final ponderada
        df['total_score'] = (
            weights['note_score'] * df['note_score'] +
            weights['season_score'] * df['season_score'] +
            weights['budget_score'] * df['budget_score']
        )
        
        # Ordenar por puntuación total
        df = df.sort_values('total_score', ascending=False)
        
        # Asegurarse de que hay suficientes recomendaciones
        available_count = min(len(df), num_recommendations)
        if available_count == 0:
            return []
            
        # Seleccionar perfumes top
        recommendations = df.head(available_count)
        
        # Formato final
        result = []
        for _, perfume in recommendations.iterrows():
            rec = {
                'id': perfume.get('id', ''),
                'name': perfume.get('name', perfume.get('title', 'Perfume')),
                'brand': perfume.get('brand', ''),
                'rating': perfume.get('rating', 0),
                'score': float(perfume['total_score']),
                'note_match': float(perfume['note_score']),
                'season_match': float(perfume['season_score'])
            }
            
            # Añadir precio si está disponible
            if 'price' in perfume and perfume['price'] and not pd.isna(perfume['price']):
                rec['price'] = perfume['price']
            
            # Añadir género si está disponible
            if 'gender' in perfume and perfume['gender'] and not pd.isna(perfume['gender']):
                rec['gender'] = perfume['gender']
                
            # Añadir notas si están disponibles
            if 'processed_notes' in perfume and isinstance(perfume['processed_notes'], list) and len(perfume['processed_notes']) > 0:
                rec['notes'] = perfume['processed_notes'][:5]  # Primeras 5 notas
                
            result.append(rec)
            
        return result