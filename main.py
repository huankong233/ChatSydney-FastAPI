import os
import json
import argparse
import uvicorn
from SydneyGPT.SydneyGPT import Chatbot
from fastapi import FastAPI, WebSocket, WebSocketDisconnect


app = FastAPI()


def checkLocale(locale):
    localeList = ['en-US', 'zh-CN', 'en-IE', 'en-GB']
    if locale in localeList:
        return locale
    else:
        raise ValueError("wrong locale")


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
        raise ValueError("wrong context")


async def process_message(user_message, context, locale):
    chatbot = await Chatbot.create(cookies=loaded_cookies, proxy=args.proxy)
    try:
        async for _, response in chatbot.ask_stream(prompt=user_message, conversation_style="creative", raw=True,
                                                    webpage_context=context, search_result=True, locale=locale):
            yield response
    except Exception as e:
        yield {"type": "error", "error": str(e)}
    finally:
        await chatbot.close()


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                request = await websocket.receive_json()
                user_message = request['message']
                context = parseContext(request['context'])
                locale = checkLocale(request.get('locale', 'zh-CN'))
                password = request.get('password', '')
                if password is not args.password:
                    raise ValueError("wrong password")
                async for response in process_message(user_message, context, locale):
                    await websocket.send_json(response)
            except WebSocketDisconnect:
                break
    except Exception as e:
        await websocket.send_json({"type": "error", "error": str(e)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", help='host for the server like "0.0.0.0"', default="0.0.0.0")
    parser.add_argument(
        "--port", help='port for the server like "65432"', default=65432)
    parser.add_argument(
        "--proxy", help='proxy for the server like "http://localhost:7890"', default="")
    parser.add_argument(
        "--cookiePath", help="cookiePath", default="cookies.json"
    )
    parser.add_argument(
        "--password", help="password", default=""
    )
    args = parser.parse_args()

    if args.proxy == '':
        print("Proxy not used")
    else:
        print(f"Proxy used: {args.proxy}")

    if os.path.isfile(args.cookiePath):
        with open(args.cookiePath, 'r') as f:
            loaded_cookies = json.load(f)
        print("Loaded cookies.json")
    else:
        loaded_cookies = []
        raise Exception("cookies.json not found")

    if args.password == '':
        print("please notice !!! you did not set the password!!!")

    uvicorn.run(app, host=args.host, port=int(args.port))
