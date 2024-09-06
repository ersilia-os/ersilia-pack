import collections


def orient_to_json(values, columns, index, orient, output_type):
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
    
    if len(output_type) > 1:
        output_type = "string"
    else:
        output_type = output_type[0].lower()

    def values_serializer(values):
        if output_type == "string":
            return [str(x) for x in values]
        if output_type == "float":
            return [float(x) for x in values]
        if output_type == "integer":
            return [int(x) for x in values]
        return values

    if orient == "split":
        data = collections.OrderedDict()
        data["columns"] = columns
        data["index"] = index
        data["data"] = values_serializer(values)
        return data

    if orient == "records":
        data = []
        for i in range(len(values)):
            record = collections.OrderedDict()
            for j in range(len(columns)):
                record[columns[j]] = values_serializer([values[i][j]])[0]
            data += [record]
        return data
    
    if orient == "index":
        data = collections.OrderedDict()
        for i in range(len(index)):
            record = collections.OrderedDict()
            for j in range(len(columns)):
                record[columns[j]] = values_serializer([values[i][j]])[0]
            data[index[i]] = record
        return data
        
    if orient == "columns":
        data = collections.OrderedDict()
        for j in range(len(columns)):
            records = collections.OrderedDict()
            for i in range(len(index)):
                records[index[i]] = values_serializer([values[i][j]])[0]
            data[columns[j]] = records
        return data

    elif orient == "values":
        return values_serializer(values)
        
    return None