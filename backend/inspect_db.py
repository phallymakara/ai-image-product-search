import asyncio
from database.cosmos import init_cosmos, get_product_container

async def inspect():
    await init_cosmos()
    container = get_product_container()
    items = container.query_items("SELECT c.id, c.productId, c.category, c.name FROM c")
    async for item in items:
        print(f"id: {item.get('id')}, productId: {item.get('productId')}, cat: {item.get('category')}, name: {item.get('name')}")

if __name__ == "__main__":
    asyncio.run(inspect())
