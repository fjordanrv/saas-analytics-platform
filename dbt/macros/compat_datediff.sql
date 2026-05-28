-- DuckDB requiere la unidad entre comillas: datediff('day', start, end)
-- Databricks/Spark la exige sin comillas:   datediff(day, start, end)
{% macro compat_datediff(unit, start_date, end_date) %}
    {% if target.type == 'databricks' %}
        datediff({{ unit }}, {{ start_date }}, {{ end_date }})
    {% else %}
        datediff('{{ unit }}', {{ start_date }}, {{ end_date }})
    {% endif %}
{% endmacro %}
