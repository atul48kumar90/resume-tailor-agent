_versions = []
_pointer = -1


def get_current_version():
    return _versions[_pointer]


def save_new_version(parent, resume, change_summary):
    global _pointer
    _versions[:] = _versions[: _pointer + 1]

    _versions.append({
        "version_id": f"v{len(_versions)}",
        "parent": parent,
        "resume": resume,
        "summary": change_summary,
    })
    _pointer += 1


def undo_version():
    global _pointer
    if _pointer > 0:
        _pointer -= 1
    return get_current_version()


def redo_version():
    global _pointer
    if _pointer < len(_versions) - 1:
        _pointer += 1
    return get_current_version()
