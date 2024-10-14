def _join_list_to_string(join_list: list):
    if len(join_list) < 1:
        return ""
    joined_list = ""
    for item in join_list:
        joined_list += f"_{item}"
    return joined_list


test = ["jedna", "dva", "tri"]
print(_join_list_to_string(test))
