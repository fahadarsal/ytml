def parse_duration(duration):
    """
    Convert a duration literal (e.g., '1m', '10s', '500ms') to seconds as a float.
    Supports:
    - 'ms' for milliseconds
    - 's' for seconds
    - 'm' for minutes
    """
    if duration.endswith("ms"):
        return float(duration[:-2]) / 1000  # Convert milliseconds to seconds
    elif duration.endswith("s"):
        return float(duration[:-1])  # Seconds
    elif duration.endswith("m"):
        return float(duration[:-1]) * 60  # Minutes to seconds
    else:
        raise ValueError(f"Invalid duration format: {duration}")


def parse_boolean(value):
    return value == 'true'
