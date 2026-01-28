import os
import time
import hashlib
import asyncio
import json
from typing import List,Tuple

import httpx
from loguru import logger

from readme import Rule

# 上游规则更新
class Updater(object):
    def __init__(self, ruleList:List[Rule]):
        self.ruleList = ruleList
        self.isNeedUpdate = False
        self.__min_change_ratio = 0.7
        self.__max_change_ratio = 1.5
        self.__min_change_abs = 1000
        self.__meta = {}
        self.__meta_path = ""

    def update(self, path:str) -> Tuple[bool,List[Rule]]:
        self.__meta_path = os.path.join(path, ".source_meta.json")
        self.__meta = self.__load_meta()
        # 启动异步循环
        loop = asyncio.get_event_loop()
        # 添加异步任务
        taskList = []
        for rule in self.ruleList:
            logger.info("updating %s..."%(rule.name))
            task = asyncio.ensure_future(self.__Download(rule, path))
            taskList.append(task)
        # 等待异步任务结束
        loop.run_until_complete(asyncio.wait(taskList))
        # 获取异步任务结果
        for task in taskList:
            new, meta_update = task.result()
            for rule in self.ruleList:
                if new.name == rule.name:
                    rule.latest = new.latest
                    rule.update = new.update
                    if rule.update:
                        self.isNeedUpdate = rule.update
                    break
            if meta_update:
                self.__meta[meta_update.get("filename")] = meta_update
        self.__save_meta()
        return self.isNeedUpdate, self.ruleList

    def __load_meta(self) -> dict:
        if not self.__meta_path or not os.path.exists(self.__meta_path):
            return {}
        try:
            with open(self.__meta_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def __save_meta(self):
        if not self.__meta_path:
            return
        try:
            with open(self.__meta_path, "w") as f:
                json.dump(self.__meta, f, indent=2, sort_keys=True)
        except Exception as e:
            logger.error("save meta failed: %s" % e)

    def __count_file_lines(self, filename: str) -> int:
        try:
            with open(filename, "r") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    def __is_probably_text(self, content: bytes) -> bool:
        sample = content[:2048]
        if b"\x00" in sample:
            return False
        lowered = sample.lstrip().lower()
        if lowered.startswith(b"<!doctype html") or b"<html" in lowered:
            return False
        return True

    def __is_anomalous_lines(self, new_lines: int, old_lines: int) -> bool:
        if old_lines < 1000:
            return False
        diff = abs(new_lines - old_lines)
        if diff < self.__min_change_abs:
            return False
        ratio = new_lines / old_lines if old_lines else 1
        return ratio < self.__min_change_ratio or ratio > self.__max_change_ratio

    def __CalcFileSha256(self, filename):
        with open(filename, "rb") as f:
            sha256obj = hashlib.sha256()
            sha256obj.update(f.read())
            hash_value = sha256obj.hexdigest()
            return hash_value

    async def __Download(self, rule:Rule, path:str) -> Tuple[Rule, dict]:
        fileName = path + "/" + rule.filename
        fileName_download = fileName + '.download'
        meta_update = None
        try:
            if os.path.exists(fileName_download):
                os.remove(fileName_download)

            async with httpx.AsyncClient() as client:
                response = await client.get(rule.url)
                response.raise_for_status()
                content = response.content
                contentType = response.headers.get("Content-Type", "").lower()
                is_text_type = contentType.startswith("text/") or "text/plain" in contentType
                if not is_text_type and not self.__is_probably_text(content):
                    raise Exception("Content-Type[%s] error"%(contentType))
                with open(fileName_download,'wb') as f:
                    f.write(content)

            if os.path.exists(fileName):
                sha256Old = self.__CalcFileSha256(fileName)
                sha256New = self.__CalcFileSha256(fileName_download)
                if sha256New != sha256Old:
                    old_lines = self.__count_file_lines(fileName)
                    new_lines = self.__count_file_lines(fileName_download)
                    if self.__is_anomalous_lines(new_lines, old_lines):
                        logger.warning("%s lines anomaly: old=%d, new=%d" % (rule.name, old_lines, new_lines))
                    rule.update = True
                else:
                    os.remove(fileName_download)
                    return rule, None
            else:
                rule.update = True

            os.replace(fileName_download, fileName)
            meta_update = {
                "filename": rule.filename,
                "sha256": self.__CalcFileSha256(fileName),
                "lines": self.__count_file_lines(fileName),
                "etag": response.headers.get("ETag", ""),
                "last_modified": response.headers.get("Last-Modified", ""),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "source_url": rule.url,
            }
        except Exception as e:
            logger.error(f'%s download failed: %s' % (rule.name, e))
        finally:
            if rule.update:
                rule.latest = time.strftime("%Y/%m/%d", time.localtime())
            logger.info("%s: latest=%s, update=%s"%(rule.name,rule.latest,rule.update))
            return rule, meta_update
