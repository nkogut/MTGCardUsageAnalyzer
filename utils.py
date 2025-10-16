def getDatesBetweenMonths(startDate: str, endDate: str) -> list[str]:
    '''
    Returns a list of every month between the start and end date (inclusive)
    Inputs can be: YYYY/MM or YYYY-MM
    Outputs are: YYYY/MM
    '''

    # Slice to remove days if invluded
    dates = []
    if "-" in startDate:
        start = startDate.split("-")[:2]
        end = endDate.split("-")[:2]
    else:
        # Handle '-' separated values as well as '/' separated
        start = startDate.split("/")[:2]
        end = endDate.split("/")[:2]
    
    start = [int(v) for v in start]
    end =   [int(v) for v in end]

    for year in range(start[0], end[0] + 1):
        yearStartMonth = 1
        yearEndMonth = 12

        if year == start[0]:
            yearStartMonth = start[1]
        if year == end[0]:
            yearEndMonth = end[1]
        
        for month in range(yearStartMonth, yearEndMonth + 1):
            dates.append(f"{year}/{month:02}")

    return dates