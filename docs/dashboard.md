# Web Dashboard

*The dashboard is currently a work in progress - functionality is still being added.*

At the moment, the dashboard provides basic diagnostic "traffic lights" to show status of various system components. The content of the reports is also reproduced.

## Installation

If you have installed all of the Python dependencies listed in the `requirement.txt` file, the web dashboard is ready to be started:

```
cd pysystemtrade/dashboard
python3 app.py
```

Visit `http://localhost:5000/` to view the dashboard. To remap this location or to make it accessible from outside machines (do this at your own peril!),
you should consult the [Flask documentation](https://flask.palletsprojects.com/)