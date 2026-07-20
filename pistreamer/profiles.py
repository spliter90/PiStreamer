from __future__ import annotations

STREAM_PROFILES: dict[str, dict[str, int | str]] = {
    "mobile_economy": {
        "label": "Mobilfunk Sparsam",
        "width": 854,
        "height": 480,
        "fps": 25,
        "video_bitrate": "800k",
        "maxrate": "1000k",
        "buffer_size": "2000k",
    },
    "mobile_standard": {
        "label": "Mobilfunk Standard",
        "width": 1280,
        "height": 720,
        "fps": 25,
        "video_bitrate": "1800k",
        "maxrate": "2200k",
        "buffer_size": "4400k",
    },
    "wifi_standard": {
        "label": "WLAN Standard",
        "width": 1280,
        "height": 720,
        "fps": 30,
        "video_bitrate": "2500k",
        "maxrate": "3000k",
        "buffer_size": "6000k",
    },
    "wifi_quality": {
        "label": "WLAN Qualität",
        "width": 1280,
        "height": 720,
        "fps": 30,
        "video_bitrate": "4000k",
        "maxrate": "4500k",
        "buffer_size": "9000k",
    },
    "lan_fullhd": {
        "label": "LAN Full HD",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "video_bitrate": "6000k",
        "maxrate": "7000k",
        "buffer_size": "14000k",
    },
}

PROFILE_ORDER = [
    "mobile_economy",
    "mobile_standard",
    "wifi_standard",
    "wifi_quality",
    "lan_fullhd",
]


def apply_profile(stream: dict, profile_name: str) -> bool:
    profile = STREAM_PROFILES.get(profile_name)
    if not profile:
        return False
    for key in ("width", "height", "fps", "video_bitrate", "maxrate", "buffer_size"):
        stream[key] = profile[key]
    stream["quality_profile"] = profile_name
    return True


def lower_profile(profile_name: str) -> str:
    if profile_name not in PROFILE_ORDER:
        return "mobile_standard"
    index = PROFILE_ORDER.index(profile_name)
    return PROFILE_ORDER[max(0, index - 1)]


def higher_profile(profile_name: str) -> str:
    if profile_name not in PROFILE_ORDER:
        return "mobile_standard"
    index = PROFILE_ORDER.index(profile_name)
    return PROFILE_ORDER[min(len(PROFILE_ORDER) - 1, index + 1)]
