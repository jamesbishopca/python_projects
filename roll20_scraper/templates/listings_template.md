# Roll20 listings for {{ today }}
Created {{ now }}

{% for system, entries in listings.items() %}
    ## {{ system }}
    {{ entries|length }} found.
    {% for entry in entries %}
        ### {{ entry.title }} :: {{ entry.gm }}
        {{ entry.desc }}
    {% endfor %}
{% endfor %}
