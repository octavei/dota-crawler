本项目会从一个特定区块开始去获取链上所有dota协议相关数据，并进行一定的过滤
# 克隆项目
```
https://github.com/octavei/dota-crawler.git
```
# 创建python虚拟环境并激活
```angular2html
python3 -m venv myenv
source myenv/bin/activate
```
# 安装依赖
```angular2html
pip install -r requirements.txt
```
# 运行爬虫
```angular2html
python main.py
```

# 测试点
1. 协议call, 最小执行单位
```angular2html
batchall(calls: remark_with_event)
```
规则：
* batchall中仅包含remark_with_event，可以多个一起使用，但是不能是其他call
* remark_with_event中必须都是json格式的数据
* remark_with_event中的json中的p字段值必须是"dot-20", "op"必须是 `["deploy", "mint", "transfer", "approve", "transferFrom", "memo"]`中的一个

2. 哪些外部交易(就是协议入口)，可以嵌套协议call
```angular2html
["batch", "batch_all", "proxy", "proxy_announced", "as_multi_threshold1", "approve_as_multi", ]
```

3. 多签模块和代理模块中的方法不能多层相互嵌套
4. 不能自己代理自己
5. 多层嵌套中，不能含有完全一模一样的batchall
