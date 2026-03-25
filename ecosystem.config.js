module.exports = {
  apps: [
    {
      name: "astock-fetcher-daily",
      script: "/opt/anaconda3/bin/python3",
      args: "-m sysinit.astock.fetcher --freq daily --universe all",
      cwd: "/Users/wenxuanliu/TradeAll/pysystemtrade",
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: "/Users/wenxuanliu/TradeAll/pysystemtrade/logs/astock-fetcher-daily-error.log",
      out_file: "/Users/wenxuanliu/TradeAll/pysystemtrade/logs/astock-fetcher-daily-out.log",
      merge_logs: true,
      env: {
        PYTHONPATH: "/Users/wenxuanliu/TradeAll/pysystemtrade",
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
