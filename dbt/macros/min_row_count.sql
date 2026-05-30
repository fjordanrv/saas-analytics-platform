{% macro test_min_row_count(model, min_rows) %}

SELECT COUNT(*) AS total
FROM {{ model }}
HAVING COUNT(*) < {{ min_rows }}

{% endmacro %}
