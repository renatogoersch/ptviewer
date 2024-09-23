import numpy as np
from sklearn.cluster import DBSCAN
from shapely.geometry import MultiPoint, Polygon
import shapely.ops
import geopandas as gpd
from pyproj import CRS, Transformer
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull

def determine_utm_crs(gdf):
    centroid = gdf.geometry.union_all().centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    hemisphere = '6' if centroid.y >= 0 else '7'
    epsg_code = 32600 + utm_zone if centroid.y >= 0 else 32700 + utm_zone
    return CRS.from_epsg(epsg_code)

def calculate_cluster_area(cluster_points):
    if len(cluster_points) < 3:
        return 0.0
    try:
        hull = ConvexHull(cluster_points)
        hull_points = cluster_points[hull.vertices]
        polygon = Polygon(hull_points)
        return polygon.area
    except Exception as e:
        print(f"Erro ao calcular área do cluster: {e}")
        return float('inf')

def optimize_dbscan_eps(gdf, eps_min=10, eps_max=500, eps_step=10, max_cluster_area=1770000):
    best_eps = None
    best_labels = None
    
    utm_crs = determine_utm_crs(gdf)
    transformer = Transformer.from_crs(gdf.crs, utm_crs, always_xy=True)
    gdf_projected = gdf.copy()
    gdf_projected['geometry'] = gdf.geometry.apply(lambda geom: shapely.ops.transform(transformer.transform, geom))
    coords = np.column_stack((gdf_projected.geometry.x, gdf_projected.geometry.y))
    
    for eps in np.arange(eps_min, eps_max + eps_step, eps_step):
        print(f"Testando EPS = {eps} metros")
        dbscan = DBSCAN(eps=eps, min_samples=5)
        labels = dbscan.fit_predict(coords)
        
        all_clusters_small = True
        unique_labels = set(labels)
        for label in unique_labels:
            if label == -1:
                continue
            cluster_coords = coords[labels == label]
            area = calculate_cluster_area(cluster_coords)
            if area > max_cluster_area:
                all_clusters_small = False
                break
        
        if all_clusters_small:
            best_eps = eps
            best_labels = labels
        else:
            break
    
    return best_eps, best_labels

def perform_dbscan_cluster_analysis(not_covered_gdf, population_column='population'):
    """
    Executa a análise de cluster DBSCAN e retorna um GeoDataFrame com os multipolygons
    cobrindo os clusters e a soma da população para cada cluster.
    
    :param not_covered_gdf: GeoDataFrame com os pontos de população não cobertos
    :param population_column: Nome da coluna que contém os dados de população
    :return: GeoDataFrame com os clusters e suas respectivas populações
    """
    if not not_covered_gdf.crs:
        not_covered_gdf.set_crs(epsg=4326, inplace=True)

    best_eps, best_labels = optimize_dbscan_eps(not_covered_gdf)

    if best_eps is not None:
        print(f"Melhor EPS encontrado: {best_eps} metros")
        not_covered_gdf['cluster'] = best_labels
        
        utm_crs = determine_utm_crs(not_covered_gdf)
        not_covered_gdf_utm = not_covered_gdf.to_crs(utm_crs)
        
        clusters_gdf = not_covered_gdf_utm.dissolve(by='cluster', aggfunc={population_column: 'sum'})
        clusters_gdf = clusters_gdf[clusters_gdf.index != -1]
        clusters_gdf['area_km2'] = clusters_gdf.geometry.area / 1e6
        clusters_gdf['geometry'] = clusters_gdf.geometry.convex_hull
        
        clusters_gdf = clusters_gdf.rename(columns={population_column: 'sum_pop'})
        clusters_gdf = clusters_gdf.reset_index()
        clusters_gdf = clusters_gdf.to_crs(epsg=4326)
        return clusters_gdf
    else:
        print("Nenhum EPS adequado encontrado. Todos os valores testados resultaram em clusters maiores que o limite especificado.")
        return None