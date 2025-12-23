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

        full_response = ""  # Track full text to update history later
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", url, json=payload, timeout=60.0) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])

                        if data['type'] == 'text':
                                # Since backend sends snapshots, calculate the new part to print
                                new_text = data['content']
                                # Only print the characters that weren't in full_response yet
                                print(new_text[len(full_response):], end="", flush=True)
                                full_response = new_text

                        elif data['type'] == 'error':
                            print(f"\n[Error]: {data['content']}")

                # Update history manually with simple dicts after the stream finishes
                # This matches the 'flexible history' logic now in your main.py
                history.append({"role": "user", "content": user_input})
                history.append({"role": "model", "content": full_response})

            except Exception as e:
                print(f"\n[Connection Error]: {e}")


if __name__ == "__main__":
    asyncio.run(test_chat())