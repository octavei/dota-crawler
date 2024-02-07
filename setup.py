from setuptools import setup, find_packages

setup(
    name='dotacrawler',
    version='0.1.16',
    packages=find_packages(),
    install_requires=[
        'websocket-client>=0.57.0,<2',
        'base58==2.1.1',
        'certifi==2023.11.17',
        'cffi==1.16.0',
        'charset-normalizer==3.3.2',
        'cytoolz==0.12.2',
        'ecdsa==0.18.0',
        'eth-hash==0.6.0',
        'eth-keys==0.5.0',
        'eth-typing==4.0.0',
        'eth-utils==2.3.1',
        'idna==3.6',
        'more-itertools==10.2.0',
        'mysql-connector==2.2.9',
        'mysql-connector-python==8.3.0',
        'py-bip39-bindings==0.1.11',
        'py-ed25519-zebra-bindings==1.0.1',
        'py-sr25519-bindings==0.2.0',
        'pycparser==2.21',
        'pycryptodome==3.20.0',
        'PyNaCl==1.5.0',
        'requests==2.31.0',
        'scalecodec==1.2.7',
        'six==1.16.0',
        'SQLAlchemy==2.0.25',
        'substrate-interface==1.7.5',
        'toolz==0.12.0',
        'typing_extensions==4.9.0',
        'urllib3==2.1.0',
        'websocket-client==1.7.0',
        'xxhash==3.4.1'
],

    # 其他设置...
)
