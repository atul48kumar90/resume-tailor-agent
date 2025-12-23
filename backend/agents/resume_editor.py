def apply_edit(resume: dict, command: dict) -> dict:
    if command["action"] == "modify_skills":
        resume["skills"] = [
            s for s in resume["skills"]
            if s not in command["remove"]
        ]

        for s in command["add"]:
            if s not in resume["skills"]:
                resume["skills"].append(s)

    return resume
