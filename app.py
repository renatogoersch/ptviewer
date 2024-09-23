import os
import pandas as pd
import geopandas as gpd
from flask import Flask, render_template, request, jsonify
from shapely.geometry import Polygon
from src.load_files import validate_files, save_files, load_gtfs_stops, create_coverage_area, load_population_data, check_population_coverage
from flask_cors import CORS
import json
from src.files_id import create_cache_entry, cache
from shapely.wkt import loads
from shapely.geometry import mapping
from src.cluster import perform_dbscan_cluster_analysis

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
async def process_files() -> dict:
    """Main function to process GTFS and population files, and return GeoJSON."""
    gtfs_file = request.files.get('gtfsFile')
    population_file = request.files.get('populationFile')
    valid, errors = validate_files(gtfs_file, population_file)
    if not valid:
        return jsonify({'status': 'error', 'errors': errors}), 400

    try:
        gtfs_path, pop_path = save_files(gtfs_file, population_file)
        stops_gdf = load_gtfs_stops(gtfs_path)
        pop_gdf = load_population_data(pop_path)
        cache_id = await create_cache_entry(stops_gdf, pop_gdf, 500)
        coverage_gdf = create_coverage_area(stops_gdf, 500)
        pop_gdf = check_population_coverage(pop_gdf, coverage_gdf)

        stops_geojson = stops_gdf.__geo_interface__
        population_geojson = pop_gdf.__geo_interface__
        coverage_geojson = coverage_gdf.__geo_interface__

        return jsonify({
            'status': 'success',
            'stops': stops_geojson,
            'coverage': 500,
            'coverage_area': coverage_geojson,
            'population': population_geojson,
            'request_id': cache_id
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'errors': [str(e)]}), 500

@app.route('/new_buffer', methods=['POST'])
async def new_buffer() -> dict:
    """Creates a new coverage area with a different buffer."""

    data = request.get_json()
    cache_id = data.get('cache_id')
    buffer = int(data.get('buffer'))
    
    if cache_id in cache:
        print('Cache ID found:', cache_id)

        stops_gdf = cache[cache_id]['stops']
        pop_gdf = cache[cache_id]['population']

        new_cache_id = await create_cache_entry(stops_gdf, pop_gdf, buffer)
        coverage_gdf = create_coverage_area(stops_gdf, buffer)
        pop_gdf = check_population_coverage(pop_gdf, coverage_gdf)

        stops_geojson = stops_gdf.__geo_interface__
        population_geojson = pop_gdf.__geo_interface__
        coverage_geojson = coverage_gdf.__geo_interface__

        return jsonify({
            'status': 'success',
            'stops': stops_geojson,
            'coverage': buffer,
            'coverage_area': coverage_geojson,
            'population': population_geojson,
            'request_id': new_cache_id
        })
    else:
        print('Cache ID not found:', cache_id)
        return jsonify({'status': 'error', 'message': 'Cache ID not found'}), 404


@app.route('/get_cache_entry', methods=['GET'])
def get_cache_entry():
    cache_id = request.args.get('cache_id')
    if cache_id:
        if cache_id in cache:
            return jsonify(cache[cache_id])
        else:
            return jsonify({'status': 'error', 'message': 'Cache ID not found'}), 404
    return jsonify(cache)


@app.route('/generate_clusters', methods=['GET'])
def generate_clusters():
    cache_id = request.args.get('cache_id')
    coverage = int(request.args.get('coverage'))
    minpop = int(request.args.get('minpop'))
    if coverage < 100 or coverage > 3000 or coverage is None:
        return jsonify({'status': 'error', 'message': 'Invalid coverage value'}), 400
    if minpop < 1 or minpop > 10000 or minpop is None:
        return jsonify({'status': 'error', 'message': 'Invalid minimum population value'}), 400
    if cache_id in cache:
        stops_gdf = cache[cache_id]['stops']
        pop_gdf = cache[cache_id]['population']

        coverage_gdf = create_coverage_area(stops_gdf, coverage)
        pop_gdf = check_population_coverage(pop_gdf, coverage_gdf)
        pop_gdf = pop_gdf[pop_gdf['covered'] == 'Not Covered']
        clusters = perform_dbscan_cluster_analysis(pop_gdf, 'number_of_people')
        clusters = clusters[clusters['sum_pop'] > minpop]
        clusters_geojson = clusters.__geo_interface__
        return jsonify(clusters_geojson)
    else:
        return jsonify({'status': 'error', 'message': 'Cache ID not found'}), 404


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
