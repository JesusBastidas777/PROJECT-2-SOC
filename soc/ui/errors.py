def describe_error(error, include_detail=False):
    short = str(error).strip() or type(error).__name__
    result = {"message": short[:240], "type": type(error).__name__}
    if include_detail:
        result["detail"] = repr(error)[:1000]
    return result
