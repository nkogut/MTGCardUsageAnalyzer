def get_dates_between_months(start_date: str, end_date: str) -> list[str]:
    '''
    Returns a list of every month between the start and end date (inclusive)
    Inputs can be: YYYY/MM or YYYY-MM
    Outputs are: YYYY/MM
    '''

    # Slice to remove days if invluded
    dates = []
    if "-" in start_date:
        start = start_date.split("-")[:2]
        end = end_date.split("-")[:2]
    else:
        # Handle '-' separated values as well as '/' separated
        start = start_date.split("/")[:2]
        end = end_date.split("/")[:2]
    
    start = [int(v) for v in start]
    end =   [int(v) for v in end]

    for year in range(start[0], end[0] + 1):
        year_start_month = 1
        year_end_month = 12

        if year == start[0]:
            year_start_month = start[1]
        if year == end[0]:
            year_end_month = end[1]
        
        for month in range(year_start_month, year_end_month + 1):
            dates.append(f"{year}/{month:02}")

    return dates