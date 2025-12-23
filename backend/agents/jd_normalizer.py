# agents/jd_normalizer.py
def normalize_jd_keywords(jd_keywords: dict) -> dict:
    """
    Canonicalize verbose JD phrases into ATS-safe forms.
    """

    CANONICAL_MAP = {
        # Architecture
        "cloud-based software architecture design and development":
            "cloud-based architecture design",
        "cloud-based software architecture":
            "cloud-based architecture design",

        # Backend scale
        "backend application development (large-scale)":
            "large-scale backend systems",
        "large-scale backend application development":
            "large-scale backend systems",

        # APIs
        "api design (modular and extensible)":
            "modular and extensible api design",

        # Databases
        "relational database design and usage":
            "relational databases",
        "nosql database design and usage":
            "nosql databases",

        # Payments
        "payments & billing domain expertise (large-scale systems)":
            "payments and billing systems",

        # Java
        "java ecosystems and frameworks":
            "java",
        "java ee (j2ee)":
            "j2ee",
    }

    def norm_list(items: list[str]) -> list[str]:
        out = []
        for k in items:
            key = k.lower().strip()
            out.append(CANONICAL_MAP.get(key, key))
        return list(dict.fromkeys(out))  # de-dup, preserve order

    return {
        "required_skills": norm_list(jd_keywords.get("required_skills", [])),
        "optional_skills": norm_list(jd_keywords.get("optional_skills", [])),
        "tools": norm_list(jd_keywords.get("tools", [])),
    }
