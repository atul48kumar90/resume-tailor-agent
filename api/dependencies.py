from fastapi import UploadFile


async def read_file(file: UploadFile) -> str:
    return (await file.read()).decode("utf-8")
