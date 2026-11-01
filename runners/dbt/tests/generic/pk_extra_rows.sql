{% test pk_extra_rows(model, key_columns) %}

-- Rows after the first for each non-null key; the failure count equals duplicate_count
with ranked as (
    select row_number() over (
        partition by {{ key_columns | join(', ') }}
        order by {{ key_columns | join(', ') }}
    ) as row_in_key
    from {{ model }}
    where {% for column in key_columns %}{{ column }} is not null{% if not loop.last %} and {% endif %}{% endfor %}
)

select *
from ranked
where row_in_key > 1

{% endtest %}