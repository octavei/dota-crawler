from logging import Logger
from substrateinterface import SubstrateInterface, Keypair, ExtrinsicReceipt
# from substrateinterface
import json
from scalecodec.types import GenericExtrinsic, is_valid_ss58_address
import hashlib


# 获取dot-20协议下的所有extrinsic信息
# 一笔交易中 不能有一模一样的两笔batchall
class RemarkCrawler:
    def __init__(self, substrate: SubstrateInterface, delay: int, start_block=0):
        self.start_block = start_block
        self.delay = delay
        # self.logger = logger
        # 代理跟签名 不能间接代理
        self.proxy_module = ["Multisig", "Proxy"]
        self.supported_extrinsic = ["batch", "batch_all", "proxy", "proxy_announced", "as_multi_threshold1", "approve_as_multi", ]
        # 支持的交易中必须有batchall
        self.must_contain_call = "batch_all"
        # batch_all中只能有remark_with_event
        self.memo_call = "remark_with_event"
        # remark中支持的协议只能是dot-20
        self.p = "dot-20"
        self.supported_ops = ["deploy", "mint", "transfer", "approve", "transferFrom", "memo"]
        self.substrate = substrate

    def get_dota_remarks_by_block_num(self, block_num: int) -> list:
        extrinsics = self.substrate.get_extrinsics(block_number=block_num)
        block_hash = self.substrate.get_block_hash(block_num)
        res = []
        for extrinsic_idx, tx in enumerate(extrinsics):
            extrinsic = tx.value.get("call").get("call_function")
            if extrinsic in self.supported_extrinsic:
                address = tx.value.get("address")
                if address is not None and is_valid_ss58_address(address, self.substrate.ss58_format):
                    print("合法地址: {}".format(address))
                    extrinsic_hash = tx.value["extrinsic_hash"]
                    call = {'call_index': '0x0000', 'call_function': 'None', 'call_module': 'None',"call_args": [{'name': 'call', 'type': 'RuntimeCall', 'value': tx.value["call"]}]}
                    b = self.get_batchalls_from_extrinsic(call, [])
                    b = self.filter_unique_batchalls(b)
                    if len(b) > 0:
                        print("---"*100)
                        # s = json.dumps(tx.value)
                        # s.replace("\'", "\"")
                        receipt = self.get_tx_receipt(extrinsic_hash, block_hash, block_num, extrinsic_idx, True)
                        if receipt.is_success:
                            e = self.filter_remarks(list(receipt.triggered_events))
                            # print("event:", e)
                            res = self.match_batchalls_with_events(address, b, e)
                            res = self.get_remarks(res=res, block_num=block_num, block_hash=block_hash,extrinsic_hash=extrinsic_hash, extrinsic_index=extrinsic_idx)
                            print("获取链上数据:\n", json.dumps(res, indent=2))

                elif address is None:
                    print("不是外部签名交易：", tx)
                else:
                    print("非法ss58地址: {}".format(address))
            else:
                print(" 不是支持的交易")

        return res

    def get_tx_receipt(self, extrinsic_hash, block_hash, block_number, extrinsic_idx, finalized):
        return ExtrinsicReceipt(self.substrate, extrinsic_hash=extrinsic_hash,
                                block_hash=block_hash,
                                                       block_number=block_number,
                                                       extrinsic_idx=extrinsic_idx, finalized=finalized)

    def get_batchalls_from_extrinsic(self, call: dict, res: list, n_proxy=0) -> list[list[tuple]]:
        # 最后向函数里传递call_args
        call_args = call["call_args"]
        for call_arg in call_args:
            if call_arg["type"] == "RuntimeCall" or call_arg["type"] == "Vec<RuntimeCall>":
                base_call = []
                if call_arg["type"] == "RuntimeCall":
                    base_call = [call_arg["value"]]
                if call_arg["type"] == "Vec<RuntimeCall>":
                    base_call = call_arg["value"]

                for c in base_call:
                    if c["call_module"] in self.proxy_module:
                        n_proxy += 1
                    if c["call_module"] in self.proxy_module and n_proxy == 2:
                        n_proxy = 1
                        continue
                    if c["call_function"] == self.must_contain_call and c["call_module"] == "Utility":
                        remark_calls = c["call_args"][0]["value"]
                        r = []
                        for remark_call in remark_calls:
                            if remark_call["call_function"] == self.memo_call:
                                remark_call_args = remark_call["call_args"]
                                memo = remark_call_args[0]["value"]
                                memo_hash = "0x" + hashlib.blake2b(memo.encode("utf-8"), digest_size=32).hexdigest()
                                memo_json = self.filter_vail_memo(memo)
                                memo_json = json.dumps(memo_json)
                                if memo_json == dict():
                                    break
                                user_and_memo = []
                                if n_proxy == 1:
                                    user_and_memo = ("proxy", memo_json, memo_hash)
                                else:
                                    user_and_memo = ("normal", memo_json, memo_hash)
                                r.append(user_and_memo)
                            else:
                                print("batchall中参杂非remark_with_event交易")
                                break
                        else:
                            if len(r) > 0:
                                res.append(r)
                    else:
                        return self.get_batchalls_from_extrinsic(c, res, n_proxy)
        return res

    @staticmethod
    def filter_unique_batchalls(batchall: list[list[tuple]]) -> list[list[tuple]]:
        pass
        res = []
        for batchs in batchall:
            for batch in batchs:
                res.append(batch)
        res_set = set(res)
        if len(res) != len(res_set):
            print("存在重复的batchall")
            return []
        return batchall

    @staticmethod
    def match_batchalls_with_events(origin: str, batchall_list: list[list[tuple]], event_list: list[list[dict]]) \
            -> list[list[dict]]:
        res = []
        for events in event_list:
            for batchall in batchall_list:
                if len(batchall) == len(events):
                    # 长度相同 说明可能在同一个事件中
                    remarks = []
                    for batch, event in zip(batchall, events):

                        if batch[0] == "proxy" and event["sender"] == origin:
                            break
                        if batch[2] != event["hash"]:
                            break
                        remark = {"origin": origin, "user": event["sender"], "memo": batch[1], "hash": batch[2]}
                        remarks.append(remark)
                    else:
                        res.append(remarks)
        return res

    def filter_vail_memo(self, memo: str) -> dict:
        try:
            memo_json = json.loads(memo)
        except Exception as e:
            print(f"memo: {memo}不是json格式. err: {e}")
            return dict()
        if memo_json.get("p") != self.p:
            print("非法协议{}".format(memo_json.get("p")))
            return dict()
        if memo_json.get("op") not in self.supported_ops:
            print("非法操作{}".format(memo_json.get("op")))
            return dict()
        return memo_json

    @staticmethod
    def get_remarks(res: list[list[dict]], block_num, block_hash, extrinsic_hash, extrinsic_index) -> list[dict]:
        result = []
        for b_index, batchall in enumerate(res):
            for r_index, remark in enumerate(batchall):
                result.append({"block_num": block_num, "block_hash": block_hash, "extrinsic_hash": extrinsic_hash,
                               "extrinsic_index": extrinsic_index, "batchall_index": b_index,"remark_index": r_index,
                               "remark_hash": remark["hash"], "origin": remark["origin"], "user": remark["user"], "memo": remark["memo"]})
        return result

    @staticmethod
    def filter_remarks(remark_with_event_list: list) -> list[list[dict]]:
        res = []
        batch_remark = []
        for index, remark_dict in enumerate(remark_with_event_list):
            # print(remark_dict)
            if index + 2 < len(remark_with_event_list):
                if remark_dict.value["event_id"] == "Remarked":
                    batch_remark.append(remark_dict.value["attributes"])
                    if remark_with_event_list[index + 1].value["event_id"] == "ItemCompleted" \
                            and remark_with_event_list[index + 2].value["event_id"] == "BatchCompleted":
                        res.append(batch_remark)
                        batch_remark = []

                    elif remark_with_event_list[index + 1].value["event_id"] == "ItemCompleted" and \
                            remark_with_event_list[index + 2].value["event_id"] == "Remarked":
                        continue
                    else:
                        batch_remark = []
        return res

    def crawl(self):
        while True:
            latest_block_hash = self.substrate.get_chain_finalised_head()
            latest_block_num = self.substrate.get_block_number(latest_block_hash)
            if self.start_block + self.delay <= latest_block_num:
                print(f"开始爬取区块高度为#{self.start_block}的extrinsics")
                self.get_dota_remarks_by_block_num(self.start_block)
                self.start_block += 1


if __name__ == "__main__":
    url = "wss://rect.me"
    substrate = SubstrateInterface(
        url=url,
    )
    delay = 2
    crawler = RemarkCrawler(substrate, delay, 273115)
    crawler.crawl()
