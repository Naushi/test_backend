import click
import json

from core.models.base import db as database, session as db_session
from core.models.migrations.utils import (
    check_revision,
    drop as drop_schema,
    migrate as migrate_schema,
)


def init_cli(app):
    init_cli_db(app)


def init_cli_db(app):
    @app.cli.group()
    def db():
        """
        Database management commands.
        """
        return

    @db.command()
    @click.option("--table")
    def check_migrations(table=None):
        """
        Ensure metadata and migrations are up to date.
        """
        result = check_revision("head", table)

        if result is True:
            return click.echo("Ok")

        for line in result:
            click.echo(line)

        raise click.Abort()

    @db.command()
    def create_all():
        """
        Create database schema from metadata.
        """
        database.create_all()

    @db.command()
    @click.option("--revision", default="head")
    def migrate(revision):
        """
        Upgrade database schema from migration scripts.
        """
        migrate_schema(db_session.connection(), revision)
        db_session.commit()

    @db.command()
    def drop():
        """
        Drop database schema and user defined types.
        """
        drop_schema()

    @db.command()
    @click.option("--transaction", default=100000000, type=int)
    @click.option("--user", default=1000, type=int)
    def feed(transaction, user):
        from core.models.all import Merchant, session
        from core.models.all import db as _db
        from data.merchant_name import merchant_names
        for name in merchant_names:
            Merchant(name=name).save()
        session.commit()

        engine = _db.engine
        insert_user = (
            f"""insert into "user" (email) select
             concat('user', generate_series(1, {user}), '@test.com');"""
        )
        engine.execute(
            insert_user
        )
        session.commit()

        insert_transaction = (
            f"""
            insert into transaction(amount, descriptor, user_id, executed_at)
            select amount, descriptor, user_id, executed_at from (
                select
                    generate_series(1, {transaction}),
                    (random() * 100)::decimal(6, 2) as 
                        amount,
                    (select name from merchant order by random() limit 1) as 
                        descriptor, 
                    trunc(random() * {user} + 1) as 
                        user_id,
                    NOW() - '1 year'::INTERVAL * ROUND(RANDOM() * 100) as
                        executed_at
            ) as data;
            """
        )
        engine.execute(
            insert_transaction
        )
        session.commit()

        update_transaction = (
            """
            update transaction
                set merchant_id = merchant.id
                from merchant
                    where transaction.descriptor = merchant.name;
            """
        )
        engine.execute(
            update_transaction
        )
        session.commit()
