import asyncio
import logging
import names
from websockets import WebSocketServerProtocol, serve
from websockets.exceptions import ConnectionClosedOK
import exchange
from async_log import AsyncLogger

logging.basicConfig(level=logging.INFO)


class Server:
    clients = set()
    log_file = "log.log"
    __file_logger: AsyncLogger = None

    async def logger(self):
        if self.__file_logger is None:
            self.__file_logger = AsyncLogger("%d.%m.%Y %H:%M:%S.%f")
            await self.__file_logger.set_file(self.log_file)
        return self.__file_logger

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distrubute(self, ws: WebSocketServerProtocol):
        async for message in ws:
             result = await self.message_handle(message, ws.name)
             await self.send_to_clients(f"{ws.name}: {result}")

    async def message_handle(self, message: str, user_name: str) -> str:
        result = message
        if message.startswith("exchange"):
            log = await self.logger()
            await log.log(f"{user_name}: {result}")
            result += " result:"
            kwargs, error_message = exchange.arg_parsing(message.split(" "))
            if error_message:
                result += error_message
            else:
                exchange_rates = await exchange.exchange_rates(**kwargs)
                result += exchange.response_to_html(exchange_rates)
        return result

async def main():
    server = Server()
    async with serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    asyncio.run(main())