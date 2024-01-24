from logging import Logger
from substrateinterface import SubstrateInterface, Keypair, ExtrinsicReceipt
# from substrateinterface
import json
from scalecodec.types import GenericExtrinsic, is_valid_ss58_address
import hashlib


# 获取dot-20协议下的所有extrinsic信息
class ExtrinsicCrawler:
    def __init__(self, substrate: SubstrateInterface, start_block=0):
        self.start_block = start_block
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
        self.substrate = substrate

    def get_supported_extrinsics_by_block_num(self, block_num: int) -> list:
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
                    receipt = self.get_tx_receipt(extrinsic_hash, block_hash, block_num, extrinsic_idx, True)
                    call = {'call_index': '0x0000', 'call_function': 'None', 'call_module': 'None',"call_args": [{'name': 'call', 'type': 'RuntimeCall', 'value': tx.value["call"]}]}
                    print(call)
                    r = self.get_remark_from_batchall(call, [])
                    memo_hash = hashlib.blake2b(r[0][0].encode("utf-8"), digest_size=32)
                    print(memo_hash.hexdigest())
                    print("---"*100)
                    s = json.dumps(tx.value)
                    s.replace("\'", "\"")
                    for i in receipt.triggered_events:
                        # pass
                        print(type(i.value), i.value)
                elif address is None:
                    print("不是外部签名交易：", tx)
                else:
                    print("非法ss58地址: {}".format(address))
            else:
                print(" 不是支持的交易")

        return extrinsics

    def get_tx_receipt(self, extrinsic_hash, block_hash, block_number, extrinsic_idx, finalized):
        return ExtrinsicReceipt(self.substrate, extrinsic_hash=extrinsic_hash,
                                block_hash=block_hash,
                                                       block_number=block_number,
                                                       extrinsic_idx=extrinsic_idx, finalized=finalized)

    def get_remark_from_batchall(self, call: dict, res: list, n_proxy=0) -> list:
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
                                print(memo)
                                r.append(memo)
                            else:
                                print("batchall中参杂非remark_with_event交易")
                                r = []
                                break
                        if len(r) > 0:
                            res.append(r)
                    else:
                        return self.get_remark_from_batchall(c, res, n_proxy)
        return res

    def crawl(self):
        while True:
            latest_block_hash = self.substrate.get_chain_finalised_head()
            latest_block_num = self.substrate.get_block_number(latest_block_hash)
            if self.start_block <= latest_block_num:
                print(f"开始爬取区块高度为#{self.start_block}的extrinsics")
                self.get_supported_extrinsics_by_block_num(self.start_block)
                self.start_block += 1


if __name__ == "__main__":
    url = "wss://rect.me"
    substrate = SubstrateInterface(
        url=url,
    )
    crawler = ExtrinsicCrawler(substrate, 235140)
    crawler.crawl()
