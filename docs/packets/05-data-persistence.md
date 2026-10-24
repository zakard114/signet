# 5/11 Data persistence

Postgres 16 listens on host port 5433. Data is on E:. Tables used by the checkout are `authorization_log` and `plate`. The log stores a masked card and a trace id, not the full number. The decline plate is one row. Restarting the app keeps both.

The amount ceiling is the stored institution `amount_limit`. The default is 500.
