from werkzeug.datastructures import FileStorage
import os
import pandas as pd
import geopandas as gpd
from typing import List, Tuple, Dict
from shapely.geometry import Polygon, mapping, MultiPolygon
from shapely.wkt import loads

UPLOAD_FOLDER = 'data/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def validate_files(gtfs_file: FileStorage, population_file: FileStorage) -> Tuple[bool, List[str]]:
    """Validates if the required files are provided."""
    errors = []
    if not gtfs_file:
        errors.append("GTFS file is missing.")
    if not population_file:
        errors.append("Population file is missing.")
    return (len(errors) == 0, errors) 


def save_files(gtfs_file: FileStorage, population_file: FileStorage) -> Tuple[str, str]:
    """Saves the GTFS and population files to the upload folder."""
    gtfs_path = os.path.join(UPLOAD_FOLDER, 'stops.txt')
    pop_path = os.path.join(UPLOAD_FOLDER, 'population.csv')
    gtfs_file.save(gtfs_path)
    population_file.save(pop_path)
    return gtfs_path, pop_path


def load_gtfs_stops(gtfs_path: str) -> gpd.GeoDataFrame:
    """Loads and validates GTFS stops from a file and creates a GeoDataFrame."""
    stops_df = pd.read_csv(gtfs_path)
    if not {'stop_lat', 'stop_lon'}.issubset(stops_df.columns):
        raise ValueError("GTFS stops.txt must contain stop_lat and stop_lon columns.")
    stops_gdf = gpd.GeoDataFrame(
        stops_df,
        geometry=gpd.points_from_xy(stops_df.stop_lon, stops_df.stop_lat),
        crs="EPSG:4326"
    )
    return stops_gdf


def create_coverage_area(stops_gdf: gpd.GeoDataFrame, buffer: int = 500) -> gpd.GeoDataFrame:
    """
    Cria uma área de cobertura ao bufferizar os pontos de parada e une as geometrias.
    Caso haja polígonos independentes, eles serão mantidos separados no resultado.
    
    Parâmetros:
    stops_gdf (gpd.GeoDataFrame): GeoDataFrame contendo pontos de paradas.

    Retorno:
    coverage_gdf (gpd.GeoDataFrame): GeoDataFrame com as áreas de cobertura unificadas.
    """
    stops_gdf = stops_gdf.to_crs(epsg=3857)
    stops_gdf['buffer'] = stops_gdf.geometry.buffer(buffer)
    coverage_area = stops_gdf['buffer'].unary_union
    if isinstance(coverage_area, Polygon):
        coverage_gdf = gpd.GeoDataFrame(geometry=[coverage_area], crs=stops_gdf.crs)
    elif isinstance(coverage_area, MultiPolygon):
        coverage_gdf = gpd.GeoDataFrame(geometry=list(coverage_area.geoms), crs=stops_gdf.crs)
    else:
        raise TypeError(f"Tipo de geometria inesperado: {coverage_area.geom_type}")
    coverage_gdf = coverage_gdf.to_crs(epsg=4326)
    return coverage_gdf


def load_population_data(pop_path: str) -> gpd.GeoDataFrame:
    """Loads and validates population data from a file and creates a GeoDataFrame."""
    pop_df = pd.read_csv(pop_path)
    if not {'latitude', 'longitude', 'number_of_people'}.issubset(pop_df.columns):
        raise ValueError("Population CSV must contain latitude, longitude, and number_of_people columns.")
    pop_gdf = gpd.GeoDataFrame(
        pop_df,
        geometry=gpd.points_from_xy(pop_df.longitude, pop_df.latitude),
        crs="EPSG:4326"
    )
    return pop_gdf


def check_population_coverage(pop_gdf: gpd.GeoDataFrame, coverage_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Verifica se os pontos de população estão dentro das áreas de cobertura.
    
    Parâmetros:
    pop_gdf (gpd.GeoDataFrame): GeoDataFrame contendo pontos de população.
    coverage_gdf (gpd.GeoDataFrame): GeoDataFrame contendo as áreas de cobertura (polígonos).

    Retorno:
    pop_gdf (gpd.GeoDataFrame): GeoDataFrame com uma nova coluna 'covered', indicando se o ponto está coberto.
    """
    pop_gdf = gpd.GeoDataFrame(
        pop_gdf,
        geometry=gpd.points_from_xy(pop_gdf.longitude, pop_gdf.latitude),
        crs="EPSG:4326"
    )

    pop_gdf = pop_gdf.to_crs(epsg=4326)
    joined_gdf = gpd.sjoin(pop_gdf, coverage_gdf, how="left", predicate="within")
    pop_gdf['covered'] = ~joined_gdf['index_right'].isna()
    pop_gdf['covered'] = pop_gdf['covered'].replace({True: 'Covered', False: 'Not Covered'})
    return pop_gdf


def convert_to_geojson(gdf: gpd.GeoDataFrame) -> Dict:
    """Converts a GeoDataFrame to GeoJSON."""
    return gdf.to_crs(epsg=4326).__geo_interface__
