from unittest.mock import MagicMock, AsyncMock

def make_qs_chain(
    *,
    result_for_all=None,
    result_for_first=None,
    result_for_values=None,
    count_value=None,
    exists_value=None,
    update_value=1,
    delete_value=0,
):
    """
    Chainable queryset mock with the bits we use:
      .filter(...).order_by(...).offset(...).limit(...)
      .all()/.first()/.count()/.exists()/.update()/.delete()/.values(...)
    """
    qs = MagicMock(name="QuerySetMock")

    # chainables
    for name in ("filter", "order_by", "offset", "limit"):
        setattr(qs, name, MagicMock(return_value=qs))

    # terminals
    qs.all = AsyncMock(return_value=result_for_all or [])
    qs.first = AsyncMock(return_value=result_for_first)
    qs.values = AsyncMock(return_value=result_for_values or [])
    qs.count = AsyncMock(return_value=(count_value if count_value is not None else len(result_for_all or [])))
    qs.exists = AsyncMock(return_value=(bool(exists_value) if exists_value is not None else bool(result_for_all)))
    qs.update = AsyncMock(return_value=update_value)
    qs.delete = AsyncMock(return_value=delete_value)
    return qs

