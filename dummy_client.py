import httpx
import asyncio


async def test_chat():
    url = "http://127.0.0.1:8080/chat"
    history = []

    print("--- Starting Chat Test ---")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        payload = {
            "message": user_input,
            "history": history
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)

            if response.status_code == 200:
                data = response.json()
                print(f"Agent: {data['reply']}")
                # Update history for the next turn
                history = data['new_history']
            else:
                print(f"Error {response.status_code}: {response.text}")


if __name__ == "__main__":
    asyncio.run(test_chat())