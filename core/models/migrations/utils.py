
from subprocess import Popen, PIPE
import os
import re

from copy import copy
from difflib import unified_diff
from logging import getLogger

from flask import current_app
from sqlalchemy import create_engine

from alembic.script import ScriptDirectory
from alembic.environment import MigrationContext
from alembic.operations import Operations

from ..base import db, Model


logger = getLogger(__name__)


alembic_version_table = "alembic_version"


script = ScriptDirectory(os.path.dirname(__file__))


def order_columns(sql):
    r = re.compile(r'CREATE TABLE ?["a-z_\.]*? \s*\([^;]+\);', re.MULTILINE)

    for match in r.findall(sql):
        match_lines = match.splitlines()

        sorted_lines = copy(match_lines)
        sorted_lines = sorted_lines[1:-1]
        sorted_lines[-1] = "%s," % sorted_lines[-1]
        sorted_lines.sort()
        sorted_lines.insert(0, match_lines[0])
        sorted_lines.append(match_lines[-1])

        sql = sql.replace("\n".join(match_lines), "\n".join(sorted_lines))

    return sql


def validate_line(line):
    excludes = ("-", "COPY", "\\", "SELECT")

    if len(line) == 1:
        return False

    for exclude in excludes:
        if line.startswith(exclude):
            return False

    return True


def dump_sql_create(engine, table=None):
    url = engine.url

    port = url.port

    if port is None:
        port = 5432

    command = [
        "/usr/bin/pg_dump",
        url.database,
        "-h",
        url.host,
        "-p",
        str(port),
        "-x",
        "-O",
        "--exclude-schema=views",
        "-T",
        alembic_version_table,
    ]

    if table is not None:
        command += ["-t", table]

    env = {}
    if url.username:
        env["PGUSER"] = url.username.encode("utf-8")
    if url.password:
        env["PGPASSWORD"] = url.password.encode("utf-8")

    p = Popen(command, stdout=PIPE, env=env)
    stdout, _ = p.communicate()
    assert p.returncode == 0

    sql = order_columns(stdout.decode())

    lines = []
    triggers = []
    for line in sql.splitlines(1):
        if validate_line(line):
            if line.startswith("CREATE TRIGGER"):
                triggers.append(line)
                continue

            lines.append(line)
    lines.extend(sorted(triggers))
    return lines


def get_context(connection, revision="head", downgrade=False):
    def _upgrade(rev, context):
        return script._upgrade_revs(revision, rev)

    def _downgrade(rev, context):
        return script._downgrade_revs(revision, rev)

    return MigrationContext.configure(
        connection,
        opts=dict(
            script=script,
            destination_rev=revision,
            fn=_downgrade if downgrade else _upgrade,
        )
    )


def run_migrations(context):
    with Operations.context(context):
        context.run_migrations()


def migrate(connection, revision, downgrade=False):
    """Upgrades database to given `revision`.
    :param Connection connection: The SQLAlchemy connection.
    :param str revision: An optional revision.
    """
    verb = "Downgrading" if downgrade else "Upgrading"
    logger.info(f"{verb} to {revision}")
    context = get_context(connection, revision, downgrade)
    run_migrations(context)


class DiffError(Exception):
    def __init__(self, *args, lines=None, **kwargs):
        self.lines = lines
        super().__init__(*args, **kwargs)


def check_diff(from_sql, to_sql, from_file, to_file):
    lines = [
        line
        for line in unified_diff(
            from_sql, to_sql, fromfile=from_file, tofile=to_file,
        )
    ]

    if len(lines) > 0:
        raise DiffError(lines=lines)

    return True


def check_revision(revision, table=None, step=None):
    """Checks if upgrading to given revision produces expected
    schema by comparing to metadata.
    :param string revision: The revision to check.
    :param string table: Tables to check.
    :param string step: An optional revision to check downgrade.
    """
    metadata = Model.metadata
    engine = create_engine(current_app.config["SQLALCHEMY_TEST_DATABASE_URI"])

    # Builds from migrations
    drop(engine)

    connection = engine.connect()

    step_sql = None

    if step:
        migrate(connection, step)
        step_sql = dump_sql_create(engine, table)

    migrate(connection, revision)
    migrated_sql = dump_sql_create(engine, table)

    # Builds from meta
    drop(engine)
    metadata.create_all(engine)
    from_meta_sql = dump_sql_create(engine, table)

    drop(engine)

    check_diff(from_meta_sql, migrated_sql, "metadata", "migrations")

    if step:
        migrate(connection, revision)
        migrate(connection, step, downgrade=True)
        downgrade_sql = dump_sql_create(engine, table)
        check_diff(step_sql, downgrade_sql, "upgrade", "downgrade")
        drop(engine)

    return True


def alter_enum(op, name, modifier):
    # An enum can't be altered within a transaction
    connection = op.get_bind().engine.raw_connection()

    try:
        op.execute("commit;")

        with connection.cursor() as cursor:
            # Sadly a new cursor always comes with an
            # initialized transaction.
            cursor.execute("rollback;")
            cursor.execute('alter type "%s" %s;' % (name, modifier))

        op.execute("begin;")

    finally:
        cursor.close()


def drop(engine=None):
    if engine is None:
        engine = db.engine

    engine.execute(
        """
        drop schema if exists audit cascade;
        DO $$ DECLARE
        r RECORD;
        BEGIN
        FOR r IN (
            SELECT  proname
            FROM    pg_catalog.pg_namespace n
            JOIN    pg_catalog.pg_proc p
            ON      pronamespace = n.oid
            WHERE   nspname = current_schema() and probin is null
        ) LOOP
            EXECUTE 'DROP FUNCTION IF EXISTS '
            || quote_ident(r.proname)
            || ' CASCADE';
        END LOOP;
        END $$;
        commit;
        DO $$ DECLARE
        r RECORD;
        BEGIN
        FOR r IN (
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = current_schema()
        ) LOOP
            EXECUTE 'DROP TABLE IF EXISTS '
            || quote_ident(r.tablename)
            || ' CASCADE';
        END LOOP;
        END $$;
        commit;
        DO $$ DECLARE
        r RECORD;
        BEGIN
        FOR r IN (
            select
                t.typname as enum_name
            from pg_type t
                join pg_enum e on t.oid = e.enumtypid
                join pg_catalog.pg_namespace n ON n.oid = t.typnamespace
            group by enum_name
        ) LOOP
            EXECUTE 'DROP TYPE IF EXISTS '
            || quote_ident(r.enum_name);
        END LOOP;
        END $$;
        commit;
        do $$ declare
        view record;
        begin
        for view in (
            select oid::regclass::text as name
            from pg_class
            where relkind = 'm'
        ) loop
            execute 'drop materialized view '
            || view.name;
        end loop;
        end $$;
        commit;
    """
    )
