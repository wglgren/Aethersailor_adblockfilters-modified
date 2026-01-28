import os
import asyncio
from typing import List,Tuple

import httpx
from loguru import logger

class RefreshCDN(object):
    def __init__(self):
        self.root = os.getcwd()
        self.targets = [
            ("rules", os.path.join(self.root, "rules")),
            ("sources/upstream", os.path.join(self.root, "sources", "upstream")),
        ]
        self.blockList = [
            "apple-cn.txt",
            "black.txt",
            "china.txt",
            "CN-ip-cidr.txt",
            "direct-list.txt",
            "domain.txt",
            "google-cn.txt",
            "myblock.txt",
            "white.txt"
        ]

    def __getRuleList(self, pwd:str) -> List[str]:
        L = []
        if not os.path.isdir(pwd):
            return L
        for fileName in os.listdir(pwd):
            if os.path.isfile(os.path.join(pwd, fileName)) and fileName not in self.blockList:
                L.append(fileName)
        return L

    async def __refresh(self, base_dir: str, fileName: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://purge.jsdelivr.net/gh/Aethersailor/adblockfilters-modified@main/%s/%s"
                    % (base_dir, fileName)
                )
                response.raise_for_status()
                status = response.json().get("status", "")
                logger.info(f'%s refresh status: %s' % (fileName, status))
        except Exception as e:
            logger.error(f'%s refresh failed: %s' % (fileName, e))

    def refresh(self):
        # 启动异步循环
        loop = asyncio.get_event_loop()
        # 添加异步任务
        taskList = []
        for base_dir, pwd in self.targets:
            ruleList = self.__getRuleList(pwd)
            for rule in ruleList:
                logger.info("refresh %s/%s..." % (base_dir, rule))
                task = asyncio.ensure_future(self.__refresh(base_dir, rule))
                taskList.append(task)
        # 等待异步任务结束
        if taskList:
            loop.run_until_complete(asyncio.wait(taskList))

if __name__ == '__main__':
    cdn = RefreshCDN()
    cdn.refresh()
