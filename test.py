import json
d = '{{"p": "123", "p": 1, "p": 123}}'
s = json.loads(d)

print(type(s))
print(s)