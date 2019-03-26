# Backend Developer Test

You have at your disposal the access to the testing database. This database has already be
feed with some values.

The purpose of this exercice is to know, how you write python code, document it, and test it.

## First part
We want you to write different route that allow us (without authentication)
* List transaction for a given user
* List transaction for a given merchant
* Know the different statistic on a given merchant:
    * average basket per month
    * average basket
* Same statistic for a user

Those route has to answer in less than 1sec

## Second part
Our merchant want to be able to create cashback offer. Those offer are define on a time intervall,
and give a discount percentage on each transaction made in his store.

In this part you will have to:
* write the matcher, that will linked the transaction and the merchant
* create the offer model
* create the cashback model