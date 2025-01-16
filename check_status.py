import asyncio
from services.runninghub import RunningHubAPI

async def main():
    rh = RunningHubAPI()
    status = await rh.check_account_status('42bac06c90e448eeab2f5560d98d41b9')
    print(status)

if __name__ == '__main__':
    asyncio.run(main())
