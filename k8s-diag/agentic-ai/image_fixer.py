"""
Image name typo detection helper
"""

from typing import Optional

# Common image name typos
COMMON_TYPOS = {
    "apline": "alpine",
    "latst": "latest",
    "lastest": "latest",
    "ubunut": "ubuntu",
    "ngnix": "nginx",
    "postgress": "postgres",
    "rediss": "redis",
}

def detect_and_fix_typo(image_name: str) -> Optional[str]:
    """
    Detect common typos in image names and suggest corrections
    Returns corrected image name or None if no typo detected
    """
    if ":" in image_name:
        name, tag = image_name.split(":", 1)
    else:
        name = image_name
        tag = "latest"
    
    # Check for typos in image name
    for typo, correct in COMMON_TYPOS.items():
        if typo in name.lower():
            corrected_name = name.lower().replace(typo, correct)
            return f"{corrected_name}:{tag}"
    
    # Check for typos in tag
    for typo, correct in COMMON_TYPOS.items():
        if typo in tag.lower():
            corrected_tag = tag.lower().replace(typo, correct)
            return f"{name}:{corrected_tag}"
    
    return None


def extract_image_from_description(description: str) -> Optional[str]:
    """Extract image name from pod description"""
    import re
    
    # Look for image name in description
    match = re.search(r'Image:\s+(.+?)(?:\n|$)', description)
    if match:
        return match.group(1).strip()
    
    return None
