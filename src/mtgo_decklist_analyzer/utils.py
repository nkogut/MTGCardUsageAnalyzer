def get_dates_between_months(start_date: str, end_date: str) -> list[str]:
    """Return a list of every month between the start and end dates (inclusive).

    Inputs can be: YYYY/MM, YYYY-MM, or may include days. Outputs: YYYY/MM.
    """
    s_y, s_m = map(int, start_date.replace("-", "/").split("/")[:2])
    e_y, e_m = map(int, end_date.replace("-", "/").split("/")[:2])

    start_val = s_y * 12 + s_m - 1
    end_val = e_y * 12 + e_m - 1

    return [f"{val // 12}/{(val % 12) + 1:02}" for val in range(start_val, end_val + 1)]
