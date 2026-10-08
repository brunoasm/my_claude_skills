#!/usr/bin/env python3
"""
Validate and enrich extracted data using external API databases.
Supports common scientific databases for taxonomy, geography, chemistry, etc.

This script template includes examples for common databases. Customize for your needs.
"""

import argparse
import copy
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from urllib.parse import quote


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Validate and enrich data with external APIs'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input JSON file with cleaned extraction results from step 04'
    )
    parser.add_argument(
        '--output',
        default='validated_data.json',
        help='Output JSON file with validated and enriched data'
    )
    parser.add_argument(
        '--apis',
        required=True,
        help='JSON configuration file specifying which APIs to use and for which fields'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip API calls, only load and structure data'
    )
    return parser.parse_args()


def load_results(input_path: Path) -> Dict:
    """Load extraction results from JSON file"""
    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_api_config(config_path: Path) -> Dict:
    """Load API configuration"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_results(results: Dict, output_path: Path):
    """Save validated results to JSON file"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


# ==============================================================================
# Taxonomy validation functions
# ==============================================================================

def validate_gbif_taxonomy(scientific_name: str) -> Optional[Dict]:
    """
    Validate taxonomic name using GBIF (Global Biodiversity Information Facility).
    Returns standardized taxonomy if found.
    """
    url = f"https://api.gbif.org/v1/species/match?name={quote(scientific_name)}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('matchType') != 'NONE':
                return {
                    'matched_name': data.get('canonicalName', scientific_name),
                    'scientific_name': data.get('scientificName'),
                    'rank': data.get('rank'),
                    'kingdom': data.get('kingdom'),
                    'phylum': data.get('phylum'),
                    'class': data.get('class'),
                    'order': data.get('order'),
                    'family': data.get('family'),
                    'genus': data.get('genus'),
                    'gbif_id': data.get('usageKey'),
                    'confidence': data.get('confidence'),
                    'match_type': data.get('matchType'),
                    'status': data.get('status')
                }
    except Exception as e:
        print(f"GBIF API error for '{scientific_name}': {e}")

    return None


def validate_wfo_plant(scientific_name: str) -> Optional[Dict]:
    """
    Validate plant name using World Flora Online.
    Returns standardized plant taxonomy if found.
    """
    # WFO requires name parsing - this is a simplified example
    url = f"http://www.worldfloraonline.org/api/1.0/search?query={quote(scientific_name)}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                first_result = data['results'][0]
                return {
                    'matched_name': first_result.get('name'),
                    'scientific_name': first_result.get('scientificName'),
                    'authors': first_result.get('authors'),
                    'family': first_result.get('family'),
                    'wfo_id': first_result.get('wfoId'),
                    'status': first_result.get('status')
                }
    except Exception as e:
        print(f"WFO API error for '{scientific_name}': {e}")

    return None


# ==============================================================================
# Geography validation functions
# ==============================================================================

def validate_geonames(location: str, country: Optional[str] = None) -> Optional[Dict]:
    """
    Validate location using GeoNames.
    Note: Requires free GeoNames account and username.
    Set GEONAMES_USERNAME environment variable.
    """
    import os
    username = os.getenv('GEONAMES_USERNAME')
    if not username:
        print("Warning: GEONAMES_USERNAME not set. Skipping GeoNames validation.")
        return None

    url = f"http://api.geonames.org/searchJSON?q={quote(location)}&maxRows=1&username={username}"
    if country:
        url += f"&country={country[:2]}"  # Country code

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('geonames'):
                place = data['geonames'][0]
                return {
                    'matched_name': place.get('name'),
                    'country': place.get('countryName'),
                    'country_code': place.get('countryCode'),
                    'admin1': place.get('adminName1'),
                    'admin2': place.get('adminName2'),
                    'latitude': place.get('lat'),
                    'longitude': place.get('lng'),
                    'geonames_id': place.get('geonameId')
                }
    except Exception as e:
        print(f"GeoNames API error for '{location}': {e}")

    return None


def geocode_location(address: str) -> Optional[Dict]:
    """
    Geocode an address using OpenStreetMap Nominatim (free, no API key needed).
    Please use responsibly - add delays between calls.
    """
    url = f"https://nominatim.openstreetmap.org/search?q={quote(address)}&format=json&limit=1"
    headers = {'User-Agent': 'Scientific-PDF-Extraction/1.0'}

    try:
        time.sleep(1)  # Be nice to OSM
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                place = data[0]
                return {
                    'display_name': place.get('display_name'),
                    'latitude': place.get('lat'),
                    'longitude': place.get('lon'),
                    'osm_type': place.get('osm_type'),
                    'osm_id': place.get('osm_id'),
                    'place_rank': place.get('place_rank')
                }
    except Exception as e:
        print(f"Nominatim error for '{address}': {e}")

    return None


# ==============================================================================
# Chemistry validation functions
# ==============================================================================

def validate_pubchem_compound(compound_name: str) -> Optional[Dict]:
    """
    Validate chemical compound using PubChem.
    Returns standardized compound information.
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(compound_name)}/JSON"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'PC_Compounds' in data and data['PC_Compounds']:
                compound = data['PC_Compounds'][0]
                return {
                    'cid': compound['id']['id']['cid'],
                    'molecular_formula': compound.get('props', [{}])[0].get('value', {}).get('sval'),
                    'pubchem_url': f"https://pubchem.ncbi.nlm.nih.gov/compound/{compound['id']['id']['cid']}"
                }
    except Exception as e:
        print(f"PubChem API error for '{compound_name}': {e}")

    return None


# ==============================================================================
# Gene/Protein validation functions
# ==============================================================================

def validate_ncbi_gene(gene_symbol: str, organism: Optional[str] = None) -> Optional[Dict]:
    """
    Validate gene using NCBI Gene database.
    """
    query = gene_symbol
    if organism:
        query += f"[Gene Name] AND {organism}[Organism]"

    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gene&term={quote(query)}&retmode=json"

    try:
        response = requests.get(search_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('esearchresult', {}).get('idlist'):
                gene_id = data['esearchresult']['idlist'][0]
                return {
                    'gene_id': gene_id,
                    'ncbi_url': f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}"
                }
    except Exception as e:
        print(f"NCBI Gene API error for '{gene_symbol}': {e}")

    return None


# ==============================================================================
# Main validation orchestration
# ==============================================================================

API_VALIDATORS = {
    'gbif_taxonomy': validate_gbif_taxonomy,
    'wfo_plants': validate_wfo_plant,
    'geonames': validate_geonames,
    'geocode': geocode_location,
    'pubchem': validate_pubchem_compound,
    'ncbi_gene': validate_ncbi_gene
}


def validate_field(value: Any, api_name: str, extra_params: Dict = None) -> Optional[Dict]:
    """
    Validate a single field value using the specified API.
    """
    if not value or value == 'none' or value == '':
        return None

    validator = API_VALIDATORS.get(api_name)
    if not validator:
        print(f"Unknown API: {api_name}")
        return None

    try:
        if extra_params:
            return validator(value, **extra_params)
        else:
            return validator(value)
    except Exception as e:
        print(f"Validation error for {api_name} with value '{value}': {e}")
        return None


def iter_mappings(api_config: Dict):
    """
    Yield (path, config) from field_mappings and nested_field_mappings.
    Keys starting with '_' and non-dict values are comments and are skipped.
    """
    for section in ('field_mappings', 'nested_field_mappings'):
        for path, field_config in api_config.get(section, {}).items():
            if path.startswith('_') or not isinstance(field_config, dict):
                continue
            yield path, field_config


def find_parents(obj: Any, keys: List[str]):
    """
    Yield every dict reached by following keys from obj, descending into
    every item of any list on the way ('records.species' visits each record).
    """
    if isinstance(obj, list):
        for item in obj:
            yield from find_parents(item, keys)
    elif isinstance(obj, dict):
        if not keys:
            yield obj
        elif keys[0] in obj:
            yield from find_parents(obj[keys[0]], keys[1:])


def process_record(
    record_data: Dict,
    api_config: Dict,
    skip_validation: bool = False,
    stats: Optional[Dict] = None
) -> Dict:
    """
    Process a single paper's extracted data, validating specified fields.

    api_config maps field paths to API names. A dotted path descends into
    nested objects and lists, and the validated result is written beside the
    field it came from (so 'records.species' adds output_field to each record):
    {
        "field_mappings": {
            "species": {"api": "gbif_taxonomy", "output_field": "validated_species"}
        },
        "nested_field_mappings": {
            "records.location": {"api": "geocode", "output_field": "coordinates"}
        }
    }

    If stats is given, per-path counts of values found, validated, and
    unmatched are accumulated into it.
    """
    if skip_validation:
        return record_data

    for path, field_config in iter_mappings(api_config):
        *parent_keys, field_name = path.split('.')
        api_name = field_config.get('api')
        output_field = field_config.get('output_field', f'validated_{field_name}')
        extra_params = field_config.get('extra_params', {})
        counts = {'found': 0, 'validated': 0, 'no_match': 0}
        if stats is not None:
            counts = stats.setdefault(path, counts)

        for parent in find_parents(record_data, parent_keys):
            value = parent.get(field_name)
            if not value or value == 'none':
                continue
            counts['found'] += 1
            validated = validate_field(value, api_name, extra_params)
            if validated:
                parent[output_field] = validated
                counts['validated'] += 1
            else:
                counts['no_match'] += 1
            time.sleep(0.5)

    return record_data


def main():
    args = parse_args()

    # Load inputs
    results = load_results(Path(args.input))
    api_config = load_api_config(Path(args.apis))
    print(f"Loaded {len(results)} extraction results")

    # Process each result
    validated_results = {}
    stats = {'total': 0, 'validated': 0, 'failed': 0}
    field_stats = {}

    for record_id, result in results.items():
        if result.get('status') != 'success':
            validated_results[record_id] = result
            stats['failed'] += 1
            continue

        stats['total'] += 1

        # Get extracted data
        extracted_data = result.get('extracted_data', {})

        # Deep copy so nested records in extracted_data are left as extracted
        validated_data = process_record(
            copy.deepcopy(extracted_data),
            api_config,
            args.skip_validation,
            field_stats
        )

        # Update result
        result['validated_data'] = validated_data
        validated_results[record_id] = result
        stats['validated'] += 1

    # Save results
    output_path = Path(args.output)
    save_results(validated_results, output_path)

    # Print summary
    print(f"\n{'='*60}")
    print("Validation and Enrichment Summary")
    print(f"{'='*60}")
    print(f"Total records: {len(results)}")
    print(f"Processed: {stats['validated']}")
    print(f"Failed extractions: {stats['failed']}")

    if not args.skip_validation:
        print(f"\n{'Field':<40} {'found':>7} {'validated':>10} {'no match':>9}")
        for path, c in field_stats.items():
            print(f"{path:<40} {c['found']:>7} {c['validated']:>10} {c['no_match']:>9}")
        unmatched = [path for path, c in field_stats.items() if c['found'] == 0]
        if unmatched:
            print("\nWARNING: no values found for: " + ", ".join(unmatched))
            print("Check these paths against your extraction schema "
                  "(fields inside 'records' need a 'records.' prefix).")

    print(f"\nResults saved to: {output_path}")
    print(f"\nNext step: Export to analysis format")


if __name__ == '__main__':
    main()
