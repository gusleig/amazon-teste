# Amazon Availability and Price Checker

This script helps checking if an Amazon product ID is available.

Just fill the product ID and price value (if value = 0 then no price check) in the products.csv file.

If the value is higher than zero, than the script will compare with the actual value in the amazon page.
Then the alert will be sent if actual value is less than the parameter.

You can change the check interval minutes inside the code:

```
timeframe = 30 #minutes
```

For Email alerts, fill the config.ini file with your configuration.

```
[EMAIL]
email_admin = gus@gmail.com
smtp_host = smtp.com
smtp_user = user
smtp_pass = pass
smtp_port = 587
smtp_from = no-reply@email.com
```

The script gets a valid proxy from https://free-proxy-list.net/
