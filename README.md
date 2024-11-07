# APTrade

A companion project for Pysystemtrade.

## Read this first

This project is a learning journey. Finantial markets are complicated and it is a delusion to think otherwise. If you want to follow along, please do so but for the real deal, I would use the official [PySystemTrade](https://github.com/robcarver17/pysystemtrade/tree/master).


## Why another tool?

Pysystemtrade is a great tool for backtesting and trading system development. APTrade is not a new tool. It is my attempt to collect learnings when using PySystemTrade and adapt to the tech stack I want to learn. 

## Goals
 To provide a user-friendly interface for developing and deploying trading strategies on top of PySystemTrade and related libraries. Automate the process of backtesting, optimizing, and deploying trading strategies. Provide a platform for tracking experiments and monitoring trading performance.

## Features

- Develop trading strategies using PySystemTrade
- Automate backtesting and optimization
- Deploy trading strategies in real-time
- Monitor trading performance
- Track experiments using MLFlow
- Containerize the application using Docker
- Provide a user-friendly interface for monitoring and control


## Components

MLFlow for tracking experiments
Docker for containerization
Frontend for monitoring and control
Backend for data processing and trading

## Running

To run the project, simply run the following command:

```bash
docker-compose up
```


## Services and Ports


| Service Name | Port | Status |
|--------------|------| -------|
| Logger       | 9020 | Working |
| IB Gateway   | 4001 | Working |
| Airflow      | 8080 | Pending |
| MLFlow       | 5000 | Pending |
| Frontend     | 3000 | Working |
| Backend      | 8000 | Pending |
| Redis        | 6379 | Pending |
| Flower       | 5555 | Pending |
| Minio        | 9000 | Pending |


## Support

This is an open source project, maintained by one busy developer in his spare time. Same rules apply [as for upstream](https://github.com/robcarver17/pysystemtrade#a-note-on-support). It is probably not suitable for people who are not prepared to read docs, delve into code, and go deep down rabbit holes. Report a bug or feature [here](https://github.com/vcaldas/aptrade/issues). But please read [the docs](https://vcaldas.github.io/aptrade/) first



## Disclaimer

This project is for educational purposes only. It is not intended to provide financial advice or make real-time trading decisions. Trading in the stock market involves risk, and you should only invest what you can afford to lose. The author and contributors of this project are and cannot be responsible for any financial losses or damages incurred while using this software. Please consult with a licensed financial advisor before making any investment decisions.

