import httpx
import asyncio
import json


async def test_chat():
    url = "http://127.0.0.1:8080/chat"
    history = []

    print("--- Starting Streaming Chat Test ---")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        payload = {
            "message": user_input,
            "history": history
        }
        print("Agent: ", end="", flush=True)

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", url, json=payload, timeout=60.0) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])

                        if data['type'] == 'text':
                            # print only the delta or the new full content depending on library version
                            print(data['content'], end="", flush=True)

                        if data['type'] == 'history':
                            history = data['content']

                            if data['type'] == 'error':
                                print(f"\n[Error]: {data['content']}")
            except Exception as e:
                print(f"\n[Connection Error]: {e}")


if __name__ == "__main__":
    asyncio.run(test_chat())