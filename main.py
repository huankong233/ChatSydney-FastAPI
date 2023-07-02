import os
import json
import argparse
import uvicorn
from SydneyGPT.SydneyGPT import Chatbot
from fastapi import FastAPI, WebSocket, WebSocketDisconnect


app = FastAPI()


async def process_message(user_message, context):
    chatbot = await Chatbot.create(cookies=loaded_cookies, proxy=args.proxy)
    try:
        async for _, response in chatbot.ask_stream(prompt=user_message, conversation_style="creative", raw=True,
                                                    webpage_context=context, search_result=True):
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
                message = await websocket.receive_text()
                request = json.loads(message)
                user_message = request['message']
                context = request['context']
                async for response in process_message(user_message, context):
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
    args = parser.parse_args()

    if args.proxy != '':
        print(f"Proxy used: {args.proxy}")

    if os.path.isfile("cookies.json"):
        with open("cookies.json", 'r') as f:
            loaded_cookies = json.load(f)
        print("Loaded cookies.json")
    else:
        loaded_cookies = []
        raise Exception("cookies.json not found")

    uvicorn.run(app, host=args.host, port=int(args.port))
