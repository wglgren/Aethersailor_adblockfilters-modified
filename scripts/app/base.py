import os
import re
import subprocess
import time
from typing import List, Set, Dict
from abc import ABC, abstractmethod

from loguru import logger


class APPBase(ABC):
    def __init__(self, blockList:List[str], unblockList:List[str], filterDict:Dict[str,object], filterList:List[str], filterList_var:List[str], ChinaSet:Set[str], fileName:str, sourceRule:str):
        repo = self._resolve_repo()
        branch = self._resolve_branch()
        if repo:
            self.homepage:str = "https://github.com/%s" % repo
            self.source:str = "https://raw.githubusercontent.com/%s/%s/rules" % (repo, branch)
        else:
            self.homepage:str = "https://github.com/Aethersailor/adblockfilters-modified"
            self.source:str = "https://raw.githubusercontent.com/Aethersailor/adblockfilters-modified/main/rules"
        self.version:str = "%s"%(time.strftime("%Y%m%d%H%M%S", time.localtime()))
        self.time:str = "%s"%(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
        self.blockList:List[str] = blockList
        self.unblockList:List[str] = unblockList
        self.filterDict:Dict[str,object] = filterDict
        self.filterList:List[str] = filterList
        self.filterList_var:List[str] = filterList_var
        self.ChinaSet:Set[str] = ChinaSet
        self.fileName:str = fileName
        self.sourceRule:str = sourceRule
        self.blockListLite:List[str] = self.__generateDomainLiteList(self.blockList, self.ChinaSet)
        self.unblockListLite:List[str] = self.__generateDomainLiteList(self.unblockList, self.ChinaSet)
        self.filterListLite:List[str] = self.__generateFilterLiteList(self.filterDict, self.filterList, self.ChinaSet)
        self.fileNameLite:str = fileName[:self.fileName.rfind(".")] + "lite" + fileName[self.fileName.rfind("."):]

    def _resolve_repo(self) -> str:
        repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
        if repo:
            return repo
        url = self._get_git_origin_url()
        return self._parse_repo_from_url(url)

    def _resolve_branch(self) -> str:
        ref = os.environ.get("GITHUB_REF", "")
        if ref.startswith("refs/heads/"):
            return ref[len("refs/heads/"):].strip() or "main"
        for key in ("GITHUB_REF_NAME", "GITHUB_HEAD_REF", "GITHUB_BASE_REF"):
            value = os.environ.get(key)
            if value:
                return value.strip()
        try:
            output = subprocess.check_output(
                ["git", "remote", "show", "origin"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            match = re.search(r"HEAD branch: (.+)", output)
            if match:
                return match.group(1).strip()
        except Exception:
            pass
        return "main"

    def _get_git_origin_url(self) -> str:
        try:
            return subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except Exception:
            return ""

    def _parse_repo_from_url(self, url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        if url.endswith(".git"):
            url = url[:-4]
        match = re.search(r"github\\.com[:/](?P<repo>[^/]+/[^/]+)$", url)
        if match:
            return match.group("repo")
        return ""
    
    def __generateDomainLiteList(self, domainList:List[str], ChinaSet:Set[str]):
        liteList = []
        try:
            for domain in domainList:
                if domain in ChinaSet:
                    liteList.append(domain)
        except Exception as e:
            logger.error("%s"%(e))
        finally:
            return liteList

    def __generateFilterLiteList(self, filterDict:Dict[str,object], filterList:List[str], ChinaSet:Set[str]):
        liteList = []
        try:
            for filter in filterList:
                info = filterDict[filter]
                domains = getattr(info, "domains", set())
                source = getattr(info, "source", "none")
                if not domains:
                    continue
                if source in {"target", "context"} and all(domain in ChinaSet for domain in domains):
                    liteList.append(filter)
        except Exception as e:
            logger.error("%s"%(e))
        finally:
            return liteList

    @abstractmethod
    def generate(self, isLite=False):
        pass

    def generateAll(self):
        try:
            if len(self.blockList):
                self.generate()

            if len(self.blockListLite):
                self.generate(isLite=True)
        except Exception as e:
            logger.error("%s"%(e))
