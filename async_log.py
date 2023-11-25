import aiofile
from aiopath import AsyncPath
from datetime import datetime

class AsyncLogger:
    def __init__(self, date_format: str):
        self.date_format = date_format
        self.file = None

    async def set_file(self, file: str):
        path = AsyncPath(file)
        if not await path.is_file():
            await path.touch(file)
        self.file = path

    async def log(self, message: str):
        log_message = f"At {datetime.now().strftime(self.date_format)}: {message}\n"
        if self.file is None:
            print(log_message)
        else:
            async with aiofile.async_open(self.file, "a") as alog:
                await alog.write(log_message)