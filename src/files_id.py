import os
import random
import string
import json
import geopandas as gpd
import pandas as pd
from shapely import wkt

# Diretório onde os caches serão salvos
CACHE_DIR = 'data/cache'

# Cria o diretório de cache, se não existir
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Inicializa o cache
cache = {}
cache_index = {}

# Carrega o arquivo cache.json, se existir
cache_file = os.path.join(CACHE_DIR, 'cache.json')
if os.path.exists(cache_file):
    with open(cache_file, 'r') as f:
        cache_index = json.load(f)
    
    # Carrega todos os arquivos CSV de cada cache_id
    for cache_id, paths in cache_index.items():
        try:
            #read as dataframe and then convert to gdf based on the geometry column
            stops_gdf = pd.read_csv(paths['stops'])
            stops_gdf['geometry'] = stops_gdf['geometry'].apply(wkt.loads)
            stops_gdf = gpd.GeoDataFrame(stops_gdf, geometry='geometry', crs="EPSG:4326")
            population_gdf = pd.read_csv(paths['population'])
            population_gdf['geometry'] = population_gdf['geometry'].apply(wkt.loads)
            population_gdf = gpd.GeoDataFrame(population_gdf, geometry='geometry', crs="EPSG:4326")
            
            # Reconstroi o cache com os GeoDataFrames
            cache[cache_id] = {
                'stops': stops_gdf,
                'population': population_gdf
            }
            print(f"Cache {cache_id} carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o cache {cache_id}: {e}")


async def generate_random_id(byte_size=16) -> str:
    """Gera um ID aleatório de tamanho especificado."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=byte_size))


async def create_cache_entry(stops: gpd.GeoDataFrame, population: gpd.GeoDataFrame, coverage: int = 500) -> str:
    """Cria uma entrada de cache, salva os arquivos CSV e atualiza o cache.json."""
    
    # Gera um cache ID
    cache_id = await generate_random_id()
    
    # Diretório onde os arquivos CSV deste cache serão salvos
    cache_dir = os.path.join(CACHE_DIR, cache_id)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    # Salva os GeoDataFrames em arquivos CSV
    stops_csv = os.path.join(cache_dir, 'stops.csv')
    population_csv = os.path.join(cache_dir, 'population.csv')
    
    stops.to_csv(stops_csv, index=False)
    population.to_csv(population_csv, index=False)
    
    # Atualiza o cache com os GeoDataFrames e os caminhos dos arquivos
    cache[cache_id] = {
        'stops': stops,
        'ccoverage': coverage,
        'population': population
    }
    
    # Atualiza o índice de cache em cache.json
    cache_index[cache_id] = {
        'stops': stops_csv,
        'population': population_csv
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cache_index, f, indent=4)
    
    return cache_id


def load_cache_entry(cache_id: str) -> dict[str, gpd.GeoDataFrame]:
    """Carrega uma entrada do cache a partir dos arquivos CSV."""
    
    if cache_id not in cache:
        raise ValueError(f"Cache ID {cache_id} não encontrado.")
    
    return cache[cache_id]

