import asyncio
from database.cosmos import init_cosmos, get_product_container

async def check():
    await init_cosmos()
    container = get_product_container()
    items = container.query_items("SELECT * FROM c")
    async for item in items:
        print(f"ID: {item.get('productId')}, Name: {item.get('name')}, Image: {item.get('imageUrl')}")

if __name__ == "__main__":
    asyncio.run(check())
