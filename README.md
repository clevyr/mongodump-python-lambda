# Python mongodump

[![Badge](https://images.microbadger.com/badges/image/clevyr/mongodump-python-lambda.svg)](https://microbadger.com/images/clevyr/mongodump-python-lambda "Get your own image badge on microbadger.com")

This is a Docker-compatible Python script to make a dump of a mongo database, puts it in a gzip compressed tarfile, and pushes it to an S3 bucket.

It uses Hashicorp Vault to get the authentication

This is intended to be ran under fargate or a lambda function.

Use lambda if the total database size is less than 256 MB due to disk limitations, otherwise use fargate.

Make sure the lambda or fargate container has IAM access to `s3:PutObject and ses:SendEmail`

## Environment Variables

|    Variable    |                             Details                             |                 Example                  |
| -------------- | --------------------------------------------------------------- | ---------------------------------------- |
| VAULT_SECRET   | the secret to pull from Hashicorp's Vault                       | `secret/testing-mongo`                   |
| VAULT_TOKEN    | the token used to access the vault                              | `s.7NaWxclhAr3EE22Z8guUQXw6`             |
| VAULT_HOST     | the vault instance to connect to                                | `https://vault.domain.com`               |
| BUCKET_NAME    | The S3 bucket to upload the backup to                           | `example-dev-backups`                    |
| MONGO_HOST     | The mongo database to backup                                    | `database`                               |
| MONGO_USERNAME | The mongo username to authenticate with                         | `username`                               |
| MONGO_PASSWORD | The mongo password to authenticate with                         | `password`                               |
| SES_REGION     | The region that SES is working in                               | `us-east-1`                              |
| EMAIL_FROM     | The email address to send emails from                           | `backups@domain.com`                     |
| EMAIL_TO       | The list of email addresses to send to, separated by semicolons | `user@domain.com;user1@domain.com`       |
| SLACK_WEBHOOK  | The webhook url to post to slack on error                       | `https://hooks.slack.com/services/x/x/x` |
## Creating a Lambda zip

Our workflow involves Docker, so we use Docker to install Linux-compatible modules. To create the lambda.zip just run `./buildzip.sh`
