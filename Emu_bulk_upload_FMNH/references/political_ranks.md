# PolPoliticalRank — Controlled Vocabulary

The Emu `Political` class uses a controlled vocabulary for `PolPoliticalRank`. The complete set of allowed values (from the Emu dropdown) is listed below. Any upload row whose `PolPoliticalRank` is not in this list will be rejected.

## Allowed values

- Arrondissement
- Autonomous Community
- Autonomous Region
- Borough
- Canton
- Census-designated Place (CDP)
- City
- Continent
- Country
- County
- Crown Dependency
- Department
- District
- Federal District
- Federal Subject
- Federal Territory
- Kingdom
- LMA
- Municipality
- Nation
- National District
- Oblast
- Oblast/Republic
- Overseas Territory
- Parish
- pd2
- pd3
- pd4
- Planet
- Plot/Transect
- Precise Locality
- Prefecture
- Province
- Province (wilaya)
- Regency
- Region
- Regional County Municipality
- Sample Area
- Satellite
- Semi-independent Entity
- Senatorial District
- Shire
- State
- Subdivision
- Subprefecture
- Territory
- Town
- Village

## Notes from Emu in-app help

- **Precise Locality** — used when the place is more specific than a city/town. Precise localities include directions and descriptions ("Bariloche, 25 km NNE via Ruta Nacional 40"). Coordinates and mapping data (TSR, elevation, etc.) go on the Site tab, not in the Locality field.
- **LMA** — Land Management Areas: National Parks, State Parks, Recreation Areas, etc.
- **City / Town** — Type the name of the city/town into the `PolLocality` field. Qualifiers and uncertainty go on the Collection Event, not here. Using "City" or "Town" in the rank causes the City/Town field to auto-populate.
- **Continent** — rarely needed. Use for continent-level names; combinations (e.g., "Europe and Asia") are allowed.
- **Country** — only for country-level names. Combinations ("France and Belgium") allowed; uncertainty goes on the Collection Event.
- **Below Country** — always use the *actual* subdivision rank (County, Department, Province, Regency, State, Territory, etc.). Do NOT include the rank in the `PolLocality` text. If the rank is unknown, fall back to `pd2`, `pd3`, or `pd4` as appropriate for the hierarchy depth.
- **Sample Area** — polygonal area defined by an ecological/environmental/collecting protocol, sitting below a political division but above Plot/Transect. Also put the sampling-area name in `SitSiteName`.
- **Plot/Transect** — named transect (linear) or plot (polygonal). Sits above Precise Locality; one plot/transect may have multiple precise localities attached. Also put the plot/transect name in `SitSiteName`.
- **IZ / CITES caveat** — do not fill in Precise Locality rank for any catalogued CITES-listed specimens; use Verbatim Locality only until Darwin Core fields are remapped with appropriate restrictions.

## Unnamed Precise Locality rule (primary coordinates)

When coordinates are *primary* (came from the sampling metadata):
- The Precise Locality node is **unnamed** — `PolLocality` is blank, `PolPoliticalRank = Precise Locality`, coordinates + elevation live on this row.
- Its parent is the most specific *named*, *non-georeferenced* node (e.g., a Village or Town). If that named node does not already exist, it must be created first (without coordinates).

This separates named geography from site-specific coordinates and keeps named nodes reusable across many collecting events.

## OSM → Emu rank mapping

When in doubt about the correct rank for a named level, query OpenStreetMap via Nominatim (`https://nominatim.openstreetmap.org/search?q=<name>,<parent>&format=jsonv2&addressdetails=1&extratags=1`) and use the response tags:

| OSM evidence | Suggested Emu rank |
|---|---|
| `type=administrative, admin_level=2` | Country |
| `type=administrative, admin_level=3` (country subdivision group) | Region / Autonomous Region |
| `type=administrative, admin_level=4` (US) | State |
| `type=administrative, admin_level=4` (BR, AR, CA) | Province / State / Territory (choose per country) |
| `type=administrative, admin_level=5` | Region / Oblast (varies) |
| `type=administrative, admin_level=6` | County / District / Department / Prefecture (varies) |
| `type=administrative, admin_level=7–8` | Municipality / City / Town |
| `place=city` | City |
| `place=town` | Town |
| `place=village` or `place=hamlet` | Village |
| `place=suburb` / `place=neighbourhood` | (no direct rank — use `Precise Locality` parent) |
| `boundary=national_park` / `leisure=park` (state/national park) | LMA |
| `boundary=protected_area` (named reserve) | LMA |
| no OSM hit, subdivision depth known | `pd2` / `pd3` / `pd4` fallback |

The rank-lookup script (`scripts/osm_rank_lookup.py`) emits a confidence level:
- **high** — unambiguous OSM hit (single matching result with clear tags).
- **medium** — multiple OSM candidates, but one clearly dominates by population / admin_level.
- **low** — no hit or several equally plausible candidates; user must confirm.
