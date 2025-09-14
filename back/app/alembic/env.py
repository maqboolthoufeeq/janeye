# Standard library imports
from logging.config import fileConfig
from pathlib import Path
import re

# Third-party imports
from alembic import context
from alembic.operations import ops
from sqlalchemy import Enum, engine_from_config, pool, text

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None

# Local application imports
from app.models import *  # noqa
from app.models.base import Base
from app.settings import settings

# We'll use the robust partition utilities inline for now

target_metadata = Base.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    return str(settings.SQLALCHEMY_DATABASE_URI)


def get_next_sequence_number():
    """
    Determine the next sequence number for migration files.

    For existing projects with legacy migrations, start from the next
    number after the total count of existing files.

    Returns:
        str: The next sequence number formatted as 4 digits (e.g., "0036")
    """
    # Get the versions directory
    script_location = config.get_main_option("script_location")
    if not script_location:
        return "0001"  # Fallback if no script location

    versions_dir = Path(script_location) / "versions"

    if not versions_dir.exists():
        return "0001"  # Fallback if versions directory doesn't exist

    # Find all migration files and extract sequence numbers
    sequence_numbers = []
    for filepath in versions_dir.glob("*.py"):
        if filepath.name.startswith("__"):
            continue

        # Look for pattern: NNNN_* at the start of filename
        match = re.match(r"^(\d{4})_", filepath.name)
        if match:
            sequence_numbers.append(int(match.group(1)))

    # If we already have sequence-numbered files, increment from the highest
    if sequence_numbers:
        return f"{max(sequence_numbers) + 1:04d}"
    else:
        # Count all existing migration files (excluding __init__.py, etc.)
        existing_files = [f for f in versions_dir.glob("*.py") if not f.name.startswith("__")]
        # Start from the next number after total existing files
        start_number = len(existing_files) + 1
        return f"{start_number:04d}"


def get_partitioned_tables():
    """
    Identify tables that are partitioned based on their __table_args__.

    Returns:
        dict: mapping of table_name -> partition_config
    """
    partitioned_tables = {}

    for table in target_metadata.tables.values():
        # Check if table has postgresql_partition_by in its info or kwargs
        partition_by = None

        # Check table.kwargs first (for SQLAlchemy 2.0+)
        if hasattr(table, "kwargs") and "postgresql_partition_by" in table.kwargs:
            partition_by = table.kwargs["postgresql_partition_by"]
        # Check table.info as fallback
        elif "postgresql_partition_by" in table.info:
            partition_by = table.info["postgresql_partition_by"]

        if partition_by:
            partitioned_tables[table.name] = {"partition_by": partition_by, "table": table}

    return partitioned_tables


def generate_partition_sql(table_name, partition_config, num_partitions=4):
    """
    Generate SQL for creating partitions based on the partition strategy.

    Args:
        table_name: Name of the main partitioned table
        partition_config: Configuration containing partition_by clause
        num_partitions: Number of partitions to create (default: 4)

    Returns:
        list: List of SQL statements to create partitions
    """
    partition_by = partition_config["partition_by"]
    sql_statements = []

    # For HASH partitioning, create numbered partitions
    if partition_by.startswith("HASH"):
        for i in range(num_partitions):
            partition_name = f"{table_name}_p{i}"
            sql = f"""
                CREATE TABLE {partition_name} PARTITION OF {table_name}
                FOR VALUES WITH (MODULUS {num_partitions}, REMAINDER {i})
            """
            sql_statements.append(sql.strip())

    # For RANGE partitioning, would need more complex logic
    # For LIST partitioning, would need value specifications
    # This can be extended based on your needs

    return sql_statements


def get_model_enum_definitions():
    """
    Extract enum definitions from SQLAlchemy models.

    Returns:
        dict: mapping of enum_type_name -> {values: [list_of_values]}
    """
    enum_definitions = {}

    for table in target_metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, Enum):
                # This is an Enum column
                enum_name = getattr(column.type, "name", None)
                if enum_name and hasattr(column.type, "enums"):
                    enum_values = list(column.type.enums)

                    enum_definitions[enum_name] = {
                        "values": enum_values,
                    }

    return enum_definitions


def generate_enum_migration_ops(enum_definitions):
    """
    Generate migration operations for enum changes.

    Args:
        enum_definitions: dict mapping enum names to their definitions

    Returns:
        tuple: (upgrade_ops, downgrade_ops)
    """
    upgrade_ops = []
    downgrade_ops = []

    # Get current database connection to check existing enum values
    try:
        bind = context.get_bind()
        if bind is None:
            # Handle offline mode - create all enums that are defined in models
            for enum_name, enum_info in enum_definitions.items():
                enum_values = enum_info["values"]

                # Create enum type first
                enum_values_str = ", ".join(f"'{v}'" for v in enum_values)
                enum_creation_sql = f"""
                    CREATE TYPE IF NOT EXISTS {enum_name} AS ENUM (
                        {enum_values_str}
                    )
                """
                upgrade_ops.append(ops.ExecuteSQLOp(enum_creation_sql.strip()))

                # For downgrade, drop the enum type
                downgrade_ops.append(ops.ExecuteSQLOp(f"DROP TYPE IF EXISTS {enum_name}"))

            return upgrade_ops, downgrade_ops

        # Query existing enum values from database
        existing_enums = {}
        result = bind.execute(
            text(
                """
            SELECT t.typname as enum_name, e.enumlabel as enum_value
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            ORDER BY t.typname, e.enumsortorder
        """
            )
        )

        for row in result:
            enum_name = row[0]
            enum_value = row[1]
            if enum_name not in existing_enums:
                existing_enums[enum_name] = []
            existing_enums[enum_name].append(enum_value)

    except Exception:
        # If we can't query the database (offline mode), create all enums
        for enum_name, enum_info in enum_definitions.items():
            enum_values = enum_info["values"]

            # Create enum type first
            enum_values_str = ", ".join(f"'{v}'" for v in enum_values)
            enum_creation_sql = f"""
                CREATE TYPE IF NOT EXISTS {enum_name} AS ENUM (
                    {enum_values_str}
                )
            """
            upgrade_ops.append(ops.ExecuteSQLOp(enum_creation_sql.strip()))

            # For downgrade, drop the enum type
            downgrade_ops.append(ops.ExecuteSQLOp(f"DROP TYPE IF EXISTS {enum_name}"))

        return upgrade_ops, downgrade_ops

    # Compare model enums with database enums
    for enum_name, enum_info in enum_definitions.items():
        model_values = set(enum_info["values"])
        db_values = set(existing_enums.get(enum_name, []))

        # If enum doesn't exist in database, create it
        if enum_name not in existing_enums:
            enum_values = enum_info["values"]
            enum_creation_sql = f"""
                CREATE TYPE {enum_name} AS ENUM ({', '.join(f"'{v}'" for v in enum_values)})
            """
            upgrade_ops.append(ops.ExecuteSQLOp(enum_creation_sql.strip()))

            # For downgrade, drop the enum type
            downgrade_ops.append(ops.ExecuteSQLOp(f"DROP TYPE IF EXISTS {enum_name}"))
        else:
            # Find new values that need to be added
            new_values = model_values - db_values

            if new_values:
                # Generate upgrade operations
                upgrade_ops.append(ops.ExecuteSQLOp(f"-- Add new enum values to {enum_name}"))

                for value in sorted(new_values):
                    upgrade_sql = f"""
                        ALTER TYPE {enum_name}
                        ADD VALUE IF NOT EXISTS '{value}';
                    """
                    upgrade_ops.append(ops.ExecuteSQLOp(upgrade_sql.strip()))

                # For downgrade, we add a comment since PostgreSQL doesn't support
                # removing enum values easily
                downgrade_ops.append(
                    ops.ExecuteSQLOp(f"-- Note: PostgreSQL doesn't support removing enum values " f"from {enum_name}.")
                )
                downgrade_ops.append(ops.ExecuteSQLOp(f"-- Removed values: {', '.join(sorted(new_values))}"))

    return upgrade_ops, downgrade_ops


def process_revision_directives(context, revision, directives):
    """
    Process revision directives to add sequence numbers, automatic partition creation,
    and automatic enum value management.
    """
    if directives:
        # Get the next sequence number
        sequence_num = get_next_sequence_number()

        # Modify the revision ID to include sequence number prefix
        for directive in directives:
            original_rev_id = directive.rev_id
            directive.rev_id = f"{sequence_num}_{original_rev_id}"

        # Auto-generate partition creation for new partitioned tables

        # Find newly created tables that are partitioned
        partitioned_tables = get_partitioned_tables()

        # Get enum definitions and generate enum migration operations
        enum_definitions = get_model_enum_definitions()
        enum_upgrade_ops, enum_downgrade_ops = generate_enum_migration_ops(enum_definitions)

        for directive in directives:
            if hasattr(directive, "upgrade_ops") and directive.upgrade_ops:
                # Look for CreateTableOp operations (create a copy to avoid modification during iteration)
                ops_to_add = []

                for op in list(directive.upgrade_ops.ops):  # Create a copy of the list
                    if isinstance(op, ops.CreateTableOp):
                        table_name = op.table_name

                        # Check if this table is partitioned
                        if table_name in partitioned_tables:
                            partition_config = partitioned_tables[table_name]

                            # Generate partition creation SQL
                            partition_sqls = generate_partition_sql(table_name, partition_config)

                            # Add comment about auto-generated partitions
                            comment_sql = f"-- Auto-generated partitions for {table_name}"
                            comment_op = ops.ExecuteSQLOp(comment_sql)
                            ops_to_add.append(comment_op)

                            # Add partition creation operations after table creation
                            for sql in partition_sqls:
                                exec_op = ops.ExecuteSQLOp(sql)
                                ops_to_add.append(exec_op)

                # Add enum operations to upgrade BEFORE other operations
                if enum_upgrade_ops:
                    directive.upgrade_ops.ops = enum_upgrade_ops + directive.upgrade_ops.ops

                # Add all the partition operations after the iteration
                directive.upgrade_ops.ops.extend(ops_to_add)

            # Auto-generate partition cleanup for downgrade
            if hasattr(directive, "downgrade_ops") and directive.downgrade_ops:
                # Collect partition drops to add before table drops
                partition_drops = []

                for op in list(directive.downgrade_ops.ops):  # Create a copy of the list
                    if isinstance(op, ops.DropTableOp):
                        table_name = op.table_name

                        # Check if this table was partitioned
                        if table_name in partitioned_tables:
                            # Generate partition drop SQL (insert before table drop)
                            drop_sqls = []
                            for i in range(4):  # Default to 4 partitions
                                partition_name = f"{table_name}_p{i}"
                                drop_sql = f"DROP TABLE IF EXISTS {partition_name}"
                                drop_sqls.append(drop_sql)

                            # Collect drops to add before this table drop
                            for drop_sql in drop_sqls:
                                exec_op = ops.ExecuteSQLOp(drop_sql)
                                partition_drops.append(exec_op)

                # Add partition drops at the beginning of downgrade operations
                directive.downgrade_ops.ops = partition_drops + directive.downgrade_ops.ops

                # Add enum operations to downgrade
                if enum_downgrade_ops:
                    directive.downgrade_ops.ops.extend(enum_downgrade_ops)


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter function for autogenerate to exclude partitioned tables and related
    objects.

    This prevents Alembic from trying to drop partitioned tables, their indexes,
    and foreign key constraints that reference them.
    """
    # Ignore partition tables (tables ending with _p followed by a number)
    if type_ == "table" and name and "_p" in name:
        # Check if it's a partition table pattern like call_history_p0, etc.
        # Use rsplit to split from the right, handling cases where table names contain _p
        parts = name.rsplit("_p", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return False

    # Ignore indexes on partition tables
    if type_ == "index" and name:
        # Pattern: tablename_p{number}_columnname_idx
        if "_p" in name and name.endswith("_idx"):
            # Use rsplit to split from the right, handling cases where table names contain _p
            parts = name.rsplit("_p", 1)
            if len(parts) >= 2:
                # Check if the part after _p starts with a digit
                second_part = parts[1].split("_")[0]
                if second_part.isdigit():
                    return False

    # Ignore foreign key constraints that reference partition tables
    if type_ == "foreign_key_constraint" and hasattr(object, "referred_table"):
        referred_table_name = object.referred_table.name
        if "_p" in referred_table_name:
            parts = referred_table_name.rsplit("_p", 1)
            if len(parts) == 2 and parts[1].isdigit():
                return False

    # Also ignore foreign key constraints with names that suggest they
    # reference partitions
    if type_ == "foreign_key_constraint" and name:
        # Pattern: action_history_organization_id_call_history_friendly_id_fkey{number}
        if "call_history_friendly_id_fkey" in name and name[-1].isdigit():
            return False

    return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        include_object=include_object,
        render_as_batch=True,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
            render_as_batch=True,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
