import asyncio
import aiohttp
from fbdsm.api import submit_mse_predictions, evaluate_tutoring
import fire

async def _mse():
    predictions_dict = {
        ('1c6afe74-c388-4eb1-b82e-8326d95e29a3', 'b09cd19f-e8f4-4587-96c7-11f2612f8040'): 3,
        ('2ee4a025-4845-47f4-a634-3c9e423a4b0e', 'a8245611-9efd-4810-95b1-f0c93c303fb7'): 1,
        ('2b9da93c-5616-49ca-999c-a894b9d004a3', 'bebd9c5a-617b-4d88-94cf-642e0675c9dc'): 5,
    }
    async with aiohttp.ClientSession() as session:
        result = await submit_mse_predictions(session, predictions_dict,set_type="mini_dev")
        print(result)

async def _tutoring():
    async with aiohttp.ClientSession() as session:
        result = await evaluate_tutoring(session,set_type="mini_dev")
        print(result)

def mse():
    return asyncio.run(_mse())

def tutoring():
    return asyncio.run(_tutoring())

if __name__ == "__main__":
    fire.Fire()
