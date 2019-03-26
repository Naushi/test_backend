# Backend Developer Test

You have at your disposal the access to the testing database. This database has already be
feed with some values.

The purpose of this exercice is to know, how you write python code, document it, and test it.

## Setup project
```shell
mkdir -p ~/.virtualenvs
python3 -m venv ~/.virtualenvs/api
source ~/.virtualenvs/api/bin/activate
pip install --upgrade pip
pip install -r requirements.txt 
```

In order to start the API you will have to export the following variable:
```bash
export FLASK_ENV=development
export FLASK_APP=core.api.main
export SERVER_NAME=localhost:5000
export SQLALCHEMY_DATABASE_URI=postgres://user:password@url/db
```
Then apply the different migrations:
```bash
flask db migrate
```
Start the development server:
````bash
flask run
````

## First part
We want you to write different route that allow us (without authentication)
* List transaction for a given user
* List transaction for a given merchant
* Know the different statistic on a given merchant:
    * average basket per month
    * average basket
* Same statistic for a user

Those route has to answer in less than 1sec on our testing database

## Second part
There is a new data set of transaction available in data/transaction.csv

We want you to use this dataset and match them with our current merchant database.
Feel free to use any library package you want.
Not all transaction can be matched so don't worry if you do not have a 100% match.

You can fork this repository and create your own README describing your API and how to use it
