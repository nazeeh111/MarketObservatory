# Contributing

Use Python 3.11+; production code uses only the standard library. Keep numerical calculations in the engine and preserve matching browser/CLI results. Add known-answer checks for numerical changes, rejection cases for new input fields, and HTTP tests for request-boundary changes. Run `python3 -m unittest discover -s tests -v` and `node --check market_observatory/static/app.js` before submitting a change. Review desktop and narrow-screen behavior when changing the interface.

Do not add credentials, personal financial records or restricted market datasets to fixtures. New demo data must be clearly synthetic or redistributable with its required notices. Keep assertions about results limited to measurements that can be reproduced.
