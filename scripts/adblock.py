import os
import argparse

from loguru import logger

from readme import ReadMe
from updater import Updater
from filter import Filter

class ADBlock(object):
    def __init__(self):
        self.root = os.getcwd()
        self.rules_dir = os.path.join(self.root, "rules")
        self.sources_dir = os.path.join(self.root, "sources")
        self.upstream_dir = os.path.join(self.sources_dir, "upstream")
        self.local_dir = os.path.join(self.sources_dir, "local")
        self.build_dir = os.path.join(self.root, "build")

    def _ensure_dirs(self):
        for path in (self.rules_dir, self.upstream_dir, self.local_dir, self.build_dir):
            os.makedirs(path, exist_ok=True)

    def refresh(self, mode: str = "all", force: bool = False):
        self._ensure_dirs()
        readme = ReadMe(self.root + '/README.md')
        ruleList = readme.getRules()
        '''
        # for test
        testList = []
        for rule in ruleList:
            if rule.type in ['filter']:
                testList.append(rule)
        #    if rule.name in ["AdGuard Mobile Ads filter"]: # "AdRules DNS List", "CJX's Annoyance List", "EasyList China", "EasyList", "EasyPrivacy", "jiekouAD", "xinggsf mv", "xinggsf rule"
        #        testList.append(rule)
        ruleList = testList
        '''
        if mode in ("all", "prepare"):
            # 更新上游规
            updater = Updater(ruleList)
            update, ruleList = updater.update(self.upstream_dir)
            if not update and not force and mode == "all":
                return

            if mode == "prepare":
                # 仅生成域名备份，用于黑名单检测
                filter = Filter(ruleList, [self.upstream_dir, self.local_dir], self.build_dir, self.rules_dir)
                filter.generate(readme.getRulesNames(), generate_rules=False, generate_domain_backup=True)
                readme.setRules(ruleList)
                readme.regenerate()
                return

        # 生成新规则
        filter = Filter(ruleList, [self.upstream_dir, self.local_dir], self.build_dir, self.rules_dir)
        generate_domain_backup = (mode == "all")
        filter.generate(readme.getRulesNames(), generate_rules=True, generate_domain_backup=generate_domain_backup)
        
        # 生成 readme.md
        readme.setRules(ruleList)
        readme.regenerate()
        

if __name__ == '__main__':
    '''
    # for test
    logFile = os.getcwd() + "/adblock.log"
    if os.path.exists(logFile):
        os.remove(logFile)
    logger.add(logFile)
    '''
    parser = argparse.ArgumentParser(description="AdBlock filter generator")
    parser.add_argument(
        "--mode",
        choices=["all", "prepare", "generate"],
        default="all",
        help="all: update+generate; prepare: update+domain backup; generate: generate rules only",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if no upstream updates are detected",
    )
    args = parser.parse_args()

    adBlock = ADBlock()
    adBlock.refresh(mode=args.mode, force=args.force)
