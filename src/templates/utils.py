import collections


def orient_to_json(values, columns, index, orient):
    """
    Convert results to the desired orientation in JSON format

    Args:
        values (list): The values to be converted.
        columns (list): The column names.
        index (list): The index values.
        orient (str): The desired orientation. Possible values are:
            - "split": Return a dictionary with "columns", "index", and "data" keys.
            - "records": Return a list of dictionaries, where each dictionary represents a record.
            - "index": Return a dictionary with index values as keys and dictionaries as values.
            - "columns": Return a dictionary with column names as keys and dictionaries as values.
            - "values": Return the values as is.

    Returns:
        The converted data in the desired orientation.

    """
    if orient == "split":
        data = collections.OrderedDict()
        data["columns"] = columns
        data["index"] = index
        data["data"] = values
        return data

    if orient == "records":
        data = []
        for i in range(len(values)):
            record = collections.OrderedDict()
            for j in range(len(columns)):
                record[columns[j]] = values[i][j]
            data += [record]
        return data
    
    if orient == "index":
        data = collections.OrderedDict()
        for i in range(len(index)):
            record = collections.OrderedDict()
            for j in range(len(columns)):
                record[columns[j]] = values[i][j]
            data[index[i]] = record
        return data
        
    if orient == "columns":
        data = collections.OrderedDict()
        for j in range(len(columns)):
            records = collections.OrderedDict()
            for i in range(len(index)):
                records[index[i]] = values[i][j]
            data[columns[j]] = records
        return data

    elif orient == "values":
        return values
        
    return None