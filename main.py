import os
import json
import argparse
import uvicorn
import logging.config
from EdgeGPT.EdgeGPT import Chatbot
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uuid

log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "[%(asctime)s] %(levelprefix)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '[%(asctime)s] %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s %(response_time)s',
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "main": {
            "level": "DEBUG",
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["access"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(log_config)
logger = logging.getLogger("main")

app = FastAPI()


def checkLocale(locale):
    localeList = ["en-US", "zh-CN", "en-IE", "en-GB"]
    if locale in localeList:
        return locale
    else:
        raise Exception("wrong locale")


def parseContext(context):
    if isinstance(context, str):
        return context
    elif isinstance(context, list):
        result = ""
        for item in context:
            tag = item["tag"]
            text = item["text"]
            result += tag + "\n" + text + "\n\n"
        return result
    else:
        raise Exception("wrong context")


async def process_message(user_message, context, locale, _U):
    if _U:
        cookies = loaded_cookies + [{"name": "_U", "value": _U}]
    else:
        cookies = loaded_cookies + [{"name": "_U", "value": str(uuid.uuid4())}]
        chatbot = await Chatbot.create(cookies=loaded_cookies, proxy=args.proxy)
        try:
            async for _, response in chatbot.ask_stream(
                prompt=user_message,
                conversation_style="creative",
                raw=True,
                webpage_context=context,
                search_result=True,
                locale=locale,
            ):
                yield response
        except Exception as e:
            yield {"type": "error", "error": str(e)}
        finally:
            await chatbot.close()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                request = await websocket.receive_json()
                user_message = request["message"]
                context = parseContext(request["context"])
                locale = checkLocale(request.get("locale", "zh-CN"))
                password = request.get("password", "")
                _U = request.get("_U", "")
                if password != args.password:
                    raise Exception("wrong password")

                async for response in process_message(
                    user_message, context, locale, _U
                ):
                    await websocket.send_json(response)
            except WebSocketDisconnect:
                break
    except Exception as e:
        await websocket.send_json({"type": "error", "error": str(e)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="host for the server", default="0.0.0.0")
    parser.add_argument("--port", help="port for the server", default=65432)
    parser.add_argument("--proxy", help="proxy for the server", default="")
    parser.add_argument("--cookiePath", help="cookiePath", default="cookies.json")
    parser.add_argument("--password", help="password", default="")
    args = parser.parse_args()

    if os.path.isfile(args.cookiePath):
        try:
            with open(args.cookiePath, "r") as f:
                loaded_cookies = json.load(f)
                logger.info("cookies is loaded")
        except Exception:
            raise Exception("wrong json file")
    else:
        raise Exception("cookies is not found")

    if args.proxy == "":
        logger.info("proxy is not used")
    else:
        logger.info(f"proxy is used with {args.proxy}")

    if args.password == "":
        logger.warning("please notice !!! you did not set the password!!!")

    uvicorn.run(app, host=args.host, port=int(args.port), log_config=log_config)
