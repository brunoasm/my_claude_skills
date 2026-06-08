#!/usr/bin/env python

### Created by Bruno de Medeiros, starting on 30-jan-2026
### Prepares specimen label data for mailmerge from the specimens database.
### Adapted from data_stri/scripts/prepare_for_labels.py

import argparse
import os
import sqlite3

import numpy as np
import pandas as pd

ROMAN_MONTHS = {
    1: 'i', 2: 'ii', 3: 'iii', 4: 'iv', 5: 'v', 6: 'vi',
    7: 'vii', 8: 'viii', 9: 'ix', 10: 'x', 11: 'xi', 12: 'xii'
}


def normalize_columns(df):
    """Lowercase, strip whitespace, replace spaces with underscores."""
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    return df


def read_data(data_dir):
    insects = normalize_columns(pd.read_excel(os.path.join(data_dir, 'insects.xlsx')))
    events = normalize_columns(pd.read_excel(os.path.join(data_dir, 'events.xlsx')))
    plants = normalize_columns(pd.read_excel(os.path.join(data_dir, 'plants.xlsx')))
    return insects, events, plants


def merge_tables(insects, events, plants):
    """insects LEFT JOIN events ON event_id, then LEFT JOIN plants ON plant_id."""
    merged = insects.merge(
        events, on='event_id', how='left',
        suffixes=('_insect', '_event')
    )
    merged = merged.merge(
        plants, on='plant_id', how='left',
        suffixes=('_insevent', '_plant')
    )
    return merged


def apply_sql_filter(df, sql_query):
    """Load df into in-memory SQLite as table 'specimens' and run the SQL query."""
    conn = sqlite3.connect(':memory:')
    df.to_sql('specimens', conn, index=False, if_exists='replace')
    try:
        result = pd.read_sql_query(sql_query, conn)
    except Exception as e:
        conn.close()
        raise ValueError(
            f"SQL query failed: {e}\n"
            f"Query: {sql_query}\n"
            f"Available columns: {sorted(df.columns.tolist())}"
        )
    conn.close()
    return result


def safe_col(df, col, default=np.nan):
    """Return df[col] if it exists, else a Series filled with default."""
    if col in df.columns:
        return df[col]
    return pd.Series(default, index=df.index)


def find_column(df, candidates):
    """Return the first column name from candidates that exists in df, or None."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


def format_coordinate(series, neg_prefix, pos_prefix):
    """Format a lat/lon series: round to 5 decimals, add N/S or E/W prefix."""
    result = pd.Series('', index=series.index)
    valid = series.notna()
    rounded = series[valid].astype(float).round(5)
    formatted = rounded.abs().astype(str)
    prefix = np.where(rounded < 0, neg_prefix, pos_prefix)
    result[valid] = pd.Series(prefix, index=rounded.index) + formatted
    return result


def format_date(row):
    """Format date as day.roman_month.year, with range support."""
    try:
        day_s = int(row['day_start'])
        month_s = int(row['month_start'])
        year_s = int(row['year_start'])
    except (ValueError, TypeError):
        return ''

    start = f"{day_s}.{ROMAN_MONTHS.get(month_s, '?')}.{year_s}"

    if pd.notna(row.get('day_end')) and pd.notna(row.get('month_end')):
        try:
            day_e = int(row['day_end'])
            month_e = int(row['month_end'])
            year_e = int(row['year_end'])
        except (ValueError, TypeError):
            return start

        if year_s == year_e and month_s == month_e:
            return f"{day_s}-{day_e}.{ROMAN_MONTHS.get(month_s, '?')}.{year_s}"
        else:
            end = f"{day_e}.{ROMAN_MONTHS.get(month_e, '?')}.{year_e}"
            return f"{start}-{end}"

    return start


def format_collector(row):
    """Primary collector, appending other_collectors if present."""
    primary = row.get('primary_collector', '')
    others = row.get('other_collectors', np.nan)
    if pd.notna(primary) and pd.notna(others) and str(others).strip():
        return f"{primary}, {others}"
    return str(primary) if pd.notna(primary) else ''


def format_species(val):
    """Collapse sp.* variants to 'sp.'."""
    if pd.isna(val):
        return ''
    val = str(val)
    if val.startswith('sp.'):
        return 'sp.'
    return val


def build_label_data(merged):
    """Transform merged data into mailmerge label columns."""
    label = pd.DataFrame()

    label['sample_id'] = merged['sample_id']
    label['country'] = merged['country'].str.upper()
    label['state'] = merged['state'].str.upper()

    label['locality'] = np.where(
        merged['locality'].notna(),
        merged['locality'],
        merged['municipality']
    )

    label['lat'] = format_coordinate(merged['lat'], neg_prefix='S', pos_prefix='N')
    label['lon'] = format_coordinate(merged['lon'], neg_prefix='W', pos_prefix='E')

    alt = merged['alt']
    label['alt'] = np.where(alt.notna(), alt.astype(str) + 'm', '')

    label['date'] = merged.apply(format_date, axis=1)
    label['col'] = merged.apply(format_collector, axis=1)

    cm = safe_col(merged, 'collecting_method')
    pi = safe_col(merged, 'plant_interaction')
    label['col_method'] = np.where(
        pi.notna(),
        cm.astype(str) + ', ' + pi.astype(str),
        cm
    )

    pg = safe_col(merged, 'plant_genus')
    ps = safe_col(merged, 'plant_species')
    label['col_plant'] = np.where(
        ps.notna(),
        pg.astype(str) + ' ' + ps.astype(str),
        pg
    )

    label['plant_auth'] = safe_col(merged, 'plant_authority')
    label['certainty'] = safe_col(merged, 'certainty')
    label['higher_taxon'] = merged['higher_taxon']
    label['taxon_level'] = merged['taxon_level']
    label['species_certainty'] = safe_col(merged, 'species_certainty')

    label['species'] = merged['species'].apply(format_species)
    label['species_italicize'] = ~label['species'].str.startswith('sp.', na=False)

    label['sex'] = merged['sex']

    label['genomics_id'] = safe_col(merged, 'genomics_id')

    det_col = find_column(merged, ['det_insevent', 'det_insect', 'det'])
    label['det'] = merged[det_col] if det_col else ''

    det_year_col = find_column(merged, ['det_year_insevent', 'det_year_insect', 'det_year'])
    label['det_year'] = merged[det_year_col] if det_year_col else ''

    return label


def write_output(label_data, outpath):
    if outpath.endswith('.csv'):
        label_data.to_csv(outpath, index=False, encoding='utf-8')
    elif outpath.endswith('.xlsx'):
        label_data.to_excel(outpath, index=False)
    else:
        raise ValueError(f"Unrecognized output format: {outpath}. Use .csv or .xlsx")
    print(f"Wrote {len(label_data)} rows to {outpath}")


def main():
    parser = argparse.ArgumentParser(
        description='Prepare specimen label data for mailmerge.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''\
examples:
  %(prog)s -o labels.xlsx
  %(prog)s -o labels.csv -p pinned
  %(prog)s -o labels.xlsx -m
  %(prog)s -o labels.xlsx --sql-filter "SELECT * FROM specimens WHERE state = 'AM'"
  %(prog)s --list-columns
'''
    )
    parser.add_argument('-o', '--output', help='Output file path (.csv or .xlsx)')
    parser.add_argument('-p', '--preservation', nargs='+',
                        help='Filter by preservation type(s)')
    parser.add_argument('-m', '--make-label', action='store_true',
                        help='Include only samples with make_label=True')
    parser.add_argument('--sql-filter',
                        help='SQL SELECT statement to filter merged data. '
                             'Table name is "specimens". Column names use '
                             'underscores (e.g. collecting_method, primary_collector). '
                             'Use --list-columns to see all available columns.')
    parser.add_argument('--list-columns', action='store_true',
                        help='Print all merged column names and exit')

    args = parser.parse_args()

    if not args.list_columns and not args.output:
        parser.error('-o/--output is required unless using --list-columns')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', '..')

    insects, events, plants = read_data(data_dir)
    merged = merge_tables(insects, events, plants)

    if args.list_columns:
        print("Available columns after merge:")
        for col in sorted(merged.columns):
            print(f"  {col}")
        return

    if args.preservation:
        merged = merged.loc[merged['preservation'].isin(args.preservation)]
    if args.make_label:
        merged = merged.loc[merged['make_label'] == True]
    if args.sql_filter:
        merged = apply_sql_filter(merged, args.sql_filter)

    if len(merged) == 0:
        print("Warning: no rows matched the filter criteria.")

    label_data = build_label_data(merged)
    write_output(label_data, args.output)


if __name__ == '__main__':
    main()
