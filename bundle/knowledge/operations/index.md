# API operations

* [Filter and download statistical data](data.md) - Filter one or more indicators by topic, geography, time, dimensions and measures.
* [List geographic areas](geo-list.md) - List names, codes and selected metadata for geographies represented in ELS.
* [List geography levels](geo-levels.md) - List geography-level keys, type prefixes and optionally their area codes.
* [Look up one geographic area](geo-lookup.md) - Return a GeoJSON feature with boundary geometry and extended metadata for a GSS code.
* [List all related areas](geo-related.md) - Return parents, children, siblings and statistically similar areas.
* [List parent areas](geo-parents.md) - List parents for an area identified by GSS code.
* [List child areas](geo-children.md) - List immediate children or children at a selected geography level.
* [List sibling areas](geo-siblings.md) - List siblings sharing an immediate or selected parent level.
* [List statistically similar areas](geo-similar.md) - List cluster members and the 20 most similar areas for supported groupings.
* [Get generalised boundaries](geo-boundaries.md) - Return filtered, low-resolution boundaries as GeoJSON or TopoJSON.
* [Search areas by name](geo-search.md) - Search area names and optionally fall back to postcode autocomplete.
* [Reverse geographic lookup](geo-reverse.md) - Return areas containing a longitude and latitude.
* [Look up a full postcode](geo-postcode.md) - Return postcode coordinates and containing geographies.
* [Autocomplete a partial postcode](geo-postcode-autocomplete.md) - Return matching postcodes and coordinates for a partial postcode.
* [List indicator metadata](metadata-indicators.md) - Return metadata for indicators filtered by topic, geography and year.
* [Get one indicator's metadata](metadata-indicator.md) - Return metadata for one indicator and optionally its full dimension values.
* [List values for one indicator dimension](metadata-dimension.md) - Return possible values for a specific dimension of a specific indicator.
* [List the indicator taxonomy](metadata-taxonomy.md) - Return indicators grouped into topics and sub-topics, nested or flat.
