def merge_settings_for_save(existing_settings: dict, incoming_settings: dict) -> dict:
    merged_settings = {**existing_settings, **incoming_settings}
    if merged_settings.get("apiKey") == "***":
        merged_settings["apiKey"] = existing_settings.get("apiKey", "")
    return merged_settings
