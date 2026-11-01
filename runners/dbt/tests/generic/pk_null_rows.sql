{% test pk_null_rows(model, key_columns) %}

-- Rows where any key column is null; the failure count equals null_key_count
select *
from {{ model }}
where {% for column in key_columns %}{{ column }} is null{% if not loop.last %} or {% endif %}{% endfor %}

{% endtest %}