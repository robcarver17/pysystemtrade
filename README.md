# APTrade

A companion project for Pysystemtrade.

## Read this first

This project is a learning journey. Finantial markets are complicated and it is a delusion to think otherwise. This project is not a get-rich-quick scheme. While the money and knowledge to invest are not available, I will be working on a paper trading system. Cut some corners to have it running and keep iterating. If you want to follow along, please do so but for the real deal, I would use the official [PySystemTrade](https://github.com/robcarver17/pysystemtrade/tree/master).


## Why another tool?

Pysystemtrade is a great tool for backtesting and trading system development. However, the learning curve is steep. APTrade is not a new tool. It is my attempt to collect learnings when using PySystemTrade. As the project grows, I hope to add more features and make it more user-friendly.

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





## How this repo is organized

The main branch is where I keep my production code. The master branch is to keep a refence to the original code. 

## Disclaimer

This project is for educational purposes only. It is not intended to provide financial advice or make real-time trading decisions. Trading in the stock market involves risk, and you should only invest what you can afford to lose. The author and contributors of this project are and cannot be responsible for any financial losses or damages incurred while using this software. Please consult with a licensed financial advisor before making any investment decisions.
